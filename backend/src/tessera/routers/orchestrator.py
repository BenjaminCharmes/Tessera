import asyncio
from collections.abc import Awaitable, Callable

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from tessera.config import settings
from tessera.models.ticket import TicketStatus
from tessera.agents.github_sync import GithubSyncAgent
from tessera.services.agent_registry import AgentRegistryService
from tessera.services.sync_map import SyncMapService
from tessera.services.agent_runner import AgentRunner
from tessera.services.documentation import DocumentationService, ResultatDocumentation
from tessera.services.event_hub import EVENT_HUB
from tessera.services.carte_du_depot import CarteDuDepot
from tessera.services.git_workspace import GitWorkspaceService
from tessera.services.github_service import GitHubService
from tessera.services.github_workflow import GitHubWorkflowService
from tessera.services.autonomie import NiveauAutonomie
from tessera.services.livraison import Livraison, LivraisonService
from tessera.services.politique_run import PolitiqueRun
from tessera.services.agent_runner import OUTILS_DE_RELECTURE
from tessera.services.pipeline_plan import ROLE_PLAN
from tessera.services.providers.base import LLMProvider
from tessera.services.providers.enregistrant import ProviderEnregistrant
from tessera.services.providers.noms import ProviderInconnu
from tessera.services.providers.par_role import modele_du_role, provider_pour_role
from tessera.services.resolveur_conflit import ResolveurConflitService
from tessera.services.run_executor import executer
from tessera.services.run_lock import RUN_LOCK
from tessera.services.run_registry import RUN_REGISTRY, RunAlreadyInProgress
from tessera.services.run_recorder import RunRecorder
from tessera.services.security_auditor import SecurityAuditorService
from tessera.services.test_runner import TestRunnerService
from tessera.services.validator import ValidatorService
from tessera.services.orchestrator import (
    Orchestrator,
    OrchestratorEvent,
    PipelineResult,
)
from tessera.services.project_loader import (
    ProjectLoader,
    load_agents_config,
    load_pipeline_config,
    load_project,
)
from tessera.services.ticket_service import TicketService
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])

# Un run à la fois par projet, sur tous les points d'entrée — le même
# verrou que `/chat/run` (ticket-121).
_RUN_LOCK = RUN_LOCK


def _tours_du_role(role: str) -> int | None:
    """Returns the max_turns budget for a given pipeline role (ticket-297).

    The plan role must read the codebase to decide on an approach — it does not
    have the diff in its prompt. The reviewer has the diff and only needs to look
    around. Other roles get the global default (None → settings.llm_max_turns).
    """
    if role == ROLE_PLAN:
        return settings.llm_max_turns_plan
    if role == "reviewer":
        return settings.llm_max_turns_reviewer
    return None


_OPEN_STATUSES = {
    TicketStatus.todo,
    TicketStatus.in_progress,
    TicketStatus.in_review,
    TicketStatus.blocked,
}


class RunRequest(BaseModel):
    project_id: str
    #: Optionnel depuis ticket-128 : une file porte `ticket_ids`, un run
    #: autonome ne porte ni l'un ni l'autre.
    ticket_id: str | None = None
    ticket_ids: list[str] = Field(default_factory=list)
    mode: str = "single"
    max_tickets: int = 5
    depuis_github: bool = False


class RunStarted(BaseModel):
    """What POST /run answers: the run started, here is how to watch it."""

    run_id: str


class RunAutonomousRequest(BaseModel):
    project_id: str
    max_tickets: int = 5
    #: Tirer d'abord les issues `agent-ready` de GitHub, pour partir d'elles
    #: (ticket-084). Faux par défaut : un appel réseau vers le dépôt d'un
    #: client ne part pas sans qu'on l'ait demandé.
    depuis_github: bool = False


async def _build_project_context(project_id: str) -> str:
    """Assemble the textual context injected into every agent's prompt.

    Contains the project's ``CLAUDE.md`` (conditionally — see below), its
    active agents, its open tickets and its recent architecture decisions.
    """
    project_path = settings.ide_workspace_dir / project_id
    loader = ProjectLoader(settings.ide_workspace_dir)
    try:
        project = await loader.load_project(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    ticket_svc = TicketService(project_path, project_id)
    all_tickets = await ticket_svc.list_tickets()
    open_tickets = [t for t in all_tickets if t.status in _OPEN_STATUSES]

    decisions_path = project_path / "memory" / "decisions.md"
    recent_decisions = (
        decisions_path.read_text(encoding="utf-8") if decisions_path.exists() else ""
    )

    tickets_summary = (
        "\n".join(f"- [{t.id}] {t.title} ({t.status.value})" for t in open_tickets)
        or "_Aucun ticket ouvert._"
    )

    # Le provider SDK exécute avec `cwd` pointé sur le dossier du projet et
    # charge donc déjà le CLAUDE.md nativement : le réinjecter ici ferait
    # payer le même contenu deux fois, à chaque appel, pour chacun des six
    # agents du pipeline sur jusqu'à trois rounds de revue. Seule l'API
    # Messages (`anthropic_api`), qui n'a pas de `cwd`, en a encore besoin.
    claude_md_section = (
        f"## CLAUDE.md\n{project.raw_claude_md}\n\n"
        if settings.llm_provider != "agent_sdk"
        else ""
    )

    return (
        f"# {project_id}\n\n"
        f"{claude_md_section}"
        f"## Agents actifs\n{', '.join(project.active_agents)}\n\n"
        f"## Tickets ouverts\n{tickets_summary}\n\n"
        f"## Décisions récentes\n{recent_decisions or '_Aucune décision._'}"
    )


async def _build_orchestrator(project_id: str) -> Orchestrator:
    project_path = settings.ide_workspace_dir / project_id
    # La politique du run — autonomie, racine git, artefacts, commande de
    # tests — se lit **ici**, une fois, avant le premier agent, et voyage vers
    # chaque service qui en dépend. Relue au moment d'agir, elle obéirait à ce
    # qu'un codeur aurait écrit dans `agents.json` pendant le run (ticket-119).
    politique = PolitiqueRun.lire(project_path)
    racine_ecriture = politique.racine_ecriture(project_path)

    # Chaque rôle a son provider, déclaré dans le manifeste avec son repli
    # (ticket-188). Le reviewer relit : le sien est réduit à la lecture. Les
    # services texte→JSON n'ont aucun usage des outils fichier (ticket-044
    # review, finding 4).
    # `AgentRunner` enregistre lui-même les appels du codeur et du reviewer.
    # Les services sans outils — sécurité, validateur, documentation —
    # appellent le provider directement : `ProviderEnregistrant` les enregistre
    # à leur place (ticket-211). Envelopper aussi les premiers les compterait
    # deux fois.
    def _par_role(role: str) -> LLMProvider:
        # Le plan lit comme le reviewer : il prépare le code, il ne l'écrit pas
        # (ticket-243). Chacun a son propre budget de tours (ticket-297).
        lecture = role in ("reviewer", ROLE_PLAN)
        outils = OUTILS_DE_RELECTURE if lecture else None
        inner = provider_pour_role(
            project_path, role, tools=outils, racine_ecriture=racine_ecriture,
            project_id=project_id, max_turns=_tours_du_role(role),
        )
        return inner

    def _sans_outils(role: str) -> LLMProvider:
        inner = provider_pour_role(
            project_path, role, allow_tools=False, project_id=project_id
        )
        return ProviderEnregistrant(inner, role=role, db_path=settings.ide_db_path)

    try:
        agent_configs = load_agents_config(project_path)
        provider = _par_role("codeur")
    except ProviderInconnu as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    registry = AgentRegistryService(settings.ide_prompts_dir)

    runner = AgentRunner(
        provider, registry, db_path=settings.ide_db_path, project_path=project_path,
        provider_par_role=_par_role,
    )

    project_context = await _build_project_context(project_id)
    ticket_svc = TicketService(project_path, project_id)

    pipeline_cfg = load_pipeline_config(project_path)

    test_runner = (
        TestRunnerService(
            cwd=pipeline_cfg.test_cwd, timeout=pipeline_cfg.test_timeout_s
        )
        if pipeline_cfg.testeur_enabled
        else None
    )
    security_auditor = (
        SecurityAuditorService(
            _sans_outils("securite"), settings.ide_prompts_dir,
            model=modele_du_role(project_path, "securite"),
        )
        if pipeline_cfg.securite_enabled
        else None
    )
    validator = (
        ValidatorService(
            _sans_outils("validateur"), settings.ide_prompts_dir,
            model=modele_du_role(project_path, "validateur"),
        )
        if pipeline_cfg.validateur_enabled
        else None
    )

    git_workspace = GitWorkspaceService(project_path, politique=politique)

    from tessera.services.ci_watcher import CI_WATCHER

    return Orchestrator(
        runner=runner,
        ticket_service=ticket_svc,
        project_context=project_context,
        agent_configs=agent_configs,
        pipeline_log_path=project_path / "memory" / "pipeline-log.md",
        max_review_rounds=pipeline_cfg.max_review_rounds,
        test_runner=test_runner,
        test_command=politique.test_command,
        security_auditor=security_auditor,
        validator=validator,
        project_path=project_path,
        git_workspace=git_workspace,
        run_max_budget_usd=settings.run_max_budget_usd,
        # Le tracker vit sur le provider, qui est le seul à voir les
        # messages du SDK. `getattr` parce que le provider Messages API
        # n'a pas de quota d'abonnement à suivre (ticket-054).
        quota_tracker=getattr(provider, "quota", None),
        # Phase 1 seulement — rebase, push, PR. Phase 2 confiée à
        # CI_WATCHER via `surveiller` (ADR-051).
        livrer=_livreur(project_id, runner, politique, espace=git_workspace),
        surveiller=_surveillance_pour(project_id, runner, politique, espace=git_workspace),
        ci_watcher=CI_WATCHER,
        documenter=_documenteur(project_id, politique),
        run_recorder=RunRecorder(settings.ide_db_path),
        # Depuis la racine d'écriture, pas le dossier du projet : le projet
        # bootstrap travaille au-dessus de lui (ADR-028), et sa carte doit le
        # montrer (ticket-190).
        carte_du_depot=CarteDuDepot.depuis(project_path, politique),
    )


def _documenteur(
    project_id: str, politique: PolitiqueRun | None = None
) -> Callable[[], Awaitable[ResultatDocumentation]]:
    """Fabrique la mise à jour de documentation d'un projet (ticket-092).

    Appelée après chaque run approuvé, sur sa branche (ticket-198), pour le
    lot des tickets livrés depuis le marqueur. Sans outils — elle lit des
    tickets et rend du JSON, elle n'a aucune raison d'écrire elle-même sur le
    disque. `README.md` et `docs/` sont cherchés à la racine d'écriture : le
    projet bootstrap documente l'IDE à la racine du dépôt (ADR-028).
    """
    project_path = settings.ide_workspace_dir / project_id
    racine_doc = (politique or PolitiqueRun.lire(project_path)).racine_ecriture(project_path)

    def _fournisseur(role: str) -> tuple[LLMProvider, str | None]:
        # Deux rôles, chacun son provider et son modèle (ticket-188).
        # Enveloppé pour que les appels de documentation entrent dans
        # `agent_calls` comme les autres (ticket-211).
        inner = provider_pour_role(project_path, role, allow_tools=False, project_id=project_id)
        return (
            ProviderEnregistrant(inner, role=role, db_path=settings.ide_db_path),
            modele_du_role(project_path, role),
        )

    # Le CLAUDE.md du projet, pas celui de la racine d'écriture : pour le
    # projet bootstrap, ce serait celui de Tessera (ticket-244).
    claude_md = (
        project_path / "CLAUDE.md"
        if load_pipeline_config(project_path).doc_claude_md
        else None
    )
    service = DocumentationService(
        _fournisseur("doc-technique")[0], settings.ide_prompts_dir,
        fournisseur=_fournisseur, claude_md=claude_md,
    )

    async def documenter() -> ResultatDocumentation:
        resultat = await service.mettre_a_jour(project_path, racine_doc=racine_doc)
        if resultat.fichiers_modifies:
            _logger.info(
                "documentation_mise_a_jour",
                extra={"fichiers": resultat.fichiers_modifies},
            )
        for refus in resultat.refus:
            _logger.warning("documentation_refusee", extra={"motif": refus})
        return resultat

    return documenter


async def _sync_apres_livraison(
    livraison: Livraison,
    espace: GitWorkspaceService | None,
    politique: PolitiqueRun | None,
    base_branch: str,
) -> Livraison:
    """Sync the base ref with the remote after a delivery attempt.

    Toujours appelé après la phase 1 (succès ou exception), pour que le
    ticket suivant forke depuis `origin/<base>` et non depuis la pointe du
    ticket précédent (ADR-051).

    Cas couverts :
    - PR ouverte : `advance_base_ref()` a été appelé dans `_noter_et_pousser`
      → le sync remet `_base_ref` sur la base distante.
    - Phase 1 échouée sans PR (exception, rebase refusé) : `advance_base_ref()`
      n'a pas été appelé, mais la base distante est la bonne référence.
    - Merge (squash) : `_base_ref` pointe sur la pointe du ticket, pas sur le
      squash commit → le sync corrige le décalage (ticket-264).

    Sur un projet `commit` (pas de push), la sync est sans effet : il n'y a
    pas de distante à rejoindre.
    """
    if espace is None:
        return livraison
    # Projets commit-only : pas de distante, la sync est sans effet
    # et ne doit pas être appelée (ticket-307).
    if politique is not None and politique.autonomy is NiveauAutonomie.commit:
        return livraison
    needs_sync = (
        livraison.merged
        or livraison.pr_number is not None
        or livraison.arret is not None
    )
    if not needs_sync:
        return livraison
    raison = await espace.sync_base_depuis_distant(base_branch)
    if raison is None:
        return livraison
    return Livraison(
        etapes=livraison.etapes,
        durees_ms=livraison.durees_ms,
        arret=raison,
        conflits=livraison.conflits,
        pr_number=livraison.pr_number,
        merged=livraison.merged,
    )


def _livreur(
    project_id: str,
    runner: AgentRunner | None = None,
    politique: PolitiqueRun | None = None,
    espace: GitWorkspaceService | None = None,
) -> Callable[[PipelineResult], Awaitable[Livraison]]:
    """Fabrique la livraison de phase 1 d'un projet (ADR-051).

    N'exécute que la phase 1 : rebase, push, PR. La phase 2 (attente CI +
    merge) est confiée à `CIWatcher` via `_surveillance_pour`.

    `espace` est l'espace git de l'orchestrateur : celui dont la base sert
    de départ au ticket suivant de la file.

    Une livraison qui échoue ne fait **pas** échouer le run : le travail est
    commité, et perdre la réponse du pipeline parce que GitHub est injoignable
    ferait croire que c'est le pipeline qui a échoué. Le motif remonte dans
    `livraison.arret`, là où l'utilisateur le lira.
    """
    project_path = settings.ide_workspace_dir / project_id
    project = load_project(project_path)
    github = None
    if project.github_remote and settings.github_token:
        github = GitHubService(token=settings.github_token, repo=project.github_remote)

    # La branche de base dépend du dépôt, pas de la machine — même raison
    # qu'ADR-029 pour l'autonomie. Le réglage global reste le repli des
    # projets qui ne déclarent rien (ticket-166).
    base_branch = (
        politique.base_branch if politique else None
    ) or settings.github_base_branch

    ticket_svc = TicketService(project_path, project_id)

    async def _noter_et_pousser(ticket_id: str, pr_number: int, branch: str) -> None:
        """Write pr_number, commit and push before any merge (ticket-270).

        Called after opening the PR but before any merge, so the bookkeeping
        commit for the PR number is on the remote and no commit is stranded on
        the ticket branch after a merged PR.  Without this number the ticket
        card would keep offering to open a PR on already-merged work (ticket-205).
        A write failure never undoes an already-opened PR: it is logged instead.
        """
        try:
            await ticket_svc.set_pr_number(ticket_id, pr_number)
            git_espace: GitWorkspaceService
            if espace is None:
                git_espace = GitWorkspaceService(project_path, politique=politique)
            else:
                git_espace = espace
            await git_espace.commit_bookkeeping()
            await git_espace.push_branch(branch)
        except Exception as exc:  # noqa: BLE001 — même raison que la livraison
            _logger.warning("pr_non_notee", extra={"erreur": str(exc)})

    service = LivraisonService(
        git_workspace=GitWorkspaceService(project_path, politique=politique),
        workflow=GitHubWorkflowService(
            git_workspace=GitWorkspaceService(project_path, politique=politique),
            github=github,
            base_branch=base_branch,
            project_path=project_path,
            politique=politique,
        ),
        project_path=project_path,
        base_branch=base_branch,
        politique=politique,
        # Sans runner — appel programmatique, test — pas de résolveur : le
        # conflit annule le rebase et remonte, comme avant ticket-090.
        resolveur=(
            ResolveurConflitService(runner, project_path).resoudre
            if runner is not None
            else None
        ),
        post_pr_callback=_noter_et_pousser,
    )

    async def livrer(result: PipelineResult) -> Livraison:
        """Phase 1 seulement : rebase, push, PR. Syncing remote base after."""
        ticket = await ticket_svc.get_ticket(result.ticket_id)
        livraison: Livraison
        try:
            livraison = await service.livrer_phase_1(
                ticket_id=result.ticket_id,
                ticket_title=ticket.title if ticket else result.ticket_id,
                ticket_body=ticket.body if ticket else "",
                ticket_type=ticket.type.value if ticket else "",
                branch=result.branch,
                approuve=result.approved,
            )
        except Exception as exc:  # noqa: BLE001 — voir la docstring
            _logger.warning("livraison_echouee", extra={"erreur": str(exc)})
            livraison = Livraison(arret=f"Livraison interrompue : {exc}")
        # Syncing is always attempted so the next ticket forks from origin/<base>
        # regardless of whether this phase 1 succeeded or failed (ADR-051).
        livraison = await _sync_apres_livraison(livraison, espace, politique, base_branch)
        return livraison

    return livrer


def _surveillance_pour(
    project_id: str,
    runner: AgentRunner | None = None,
    politique: PolitiqueRun | None = None,
    espace: GitWorkspaceService | None = None,
) -> Callable[[str, str, int, "EventCallback"], Awaitable[None]]:
    """Fabrique le callback `surveiller` pour l'orchestrateur (ADR-051).

    Retourne une coroutine qui démarre la phase 2 (attente CI + merge) en
    tâche de fond via `CI_WATCHER.surveiller`. Retourne immédiatement, sans
    attendre la fin de la CI.
    """
    from tessera.services.ci_watcher import CI_WATCHER
    from tessera.services.pipeline_events import EventCallback as _CB

    project_path = settings.ide_workspace_dir / project_id
    project = load_project(project_path)
    github = None
    if project.github_remote and settings.github_token:
        github = GitHubService(token=settings.github_token, repo=project.github_remote)

    base_branch = (
        politique.base_branch if politique else None
    ) or settings.github_base_branch

    service = LivraisonService(
        git_workspace=GitWorkspaceService(project_path, politique=politique),
        workflow=GitHubWorkflowService(
            git_workspace=GitWorkspaceService(project_path, politique=politique),
            github=github,
            base_branch=base_branch,
            project_path=project_path,
            politique=politique,
        ),
        project_path=project_path,
        base_branch=base_branch,
        politique=politique,
        resolveur=(
            ResolveurConflitService(runner, project_path).resoudre
            if runner is not None
            else None
        ),
    )

    async def surveiller(
        p_id: str,
        ticket_id: str,
        pr_number: int,
        on_event: "_CB",
    ) -> None:
        """Start CI watching for pr_number in a background task."""
        await CI_WATCHER.surveiller(
            p_id,
            ticket_id,
            pr_number,
            service.livrer_phase_2,
            on_event,
        )

    return surveiller


#: Les tâches de run en vol. Sans référence forte, asyncio peut collecter
#: une tâche en cours de route : le run s'arrêterait au milieu, sans commit,
#: ce qu'ADR-018 interdit.
_TACHES: set[asyncio.Task[None]] = set()


def _ticket_initial(request: RunRequest) -> str | None:
    """Le premier ticket traité par le run — le seul connu au démarrage."""
    if request.ticket_id:
        return request.ticket_id
    if request.ticket_ids:
        return request.ticket_ids[0]
    return None


async def _lire_titre(
    ticket_svc: TicketService, ticket_id: str | None
) -> str | None:
    """Lit le titre d'un ticket ; renvoie None si illisible ou absent."""
    if not ticket_id:
        return None
    try:
        ticket = await ticket_svc.get_ticket(ticket_id)
        return ticket.title if ticket else None
    except Exception:  # noqa: BLE001
        return None


class Limites(BaseModel):
    """Les plafonds de dépense, pour que l'écran situe un coût (ticket-197)."""

    run_max_budget_usd: float
    llm_max_budget_usd: float


@router.get("/limits", response_model=Limites)
async def get_limits() -> Limites:
    return Limites(
        run_max_budget_usd=settings.run_max_budget_usd,
        llm_max_budget_usd=settings.llm_max_budget_usd,
    )


@router.post("/run", status_code=202, response_model=RunStarted)
async def run_pipeline(request: RunRequest) -> RunStarted:
    """Start a run, and answer with its id without waiting for it to end.

    Le run était porté par sa WebSocket avant ticket-128 : il n'était donc
    observable que depuis l'onglet qui l'avait ouverte. Il est maintenant une
    tâche que personne ne possède, et que `/orchestrator/observe` regarde.

    La réservation se fait **ici** et non dans la tâche : deux POST
    rapprochés passeraient tous les deux si le projet n'était marqué occupé
    qu'une fois la réponse partie (ADR-038).
    """
    if request.mode == "single" and not request.ticket_id:
        raise HTTPException(status_code=422, detail="ticket_id requis en mode single")

    # Lire le titre du ticket initial avant de réserver le run (ticket-286).
    project_path = settings.ide_workspace_dir / request.project_id
    ticket_svc = TicketService(project_path, request.project_id)
    initial_ticket_id = _ticket_initial(request)
    ticket_titre = await _lire_titre(ticket_svc, initial_ticket_id)

    try:
        run = RUN_REGISTRY.ouvrir(
            request.project_id,
            initial_ticket_id,
            mode=request.mode,
            ticket_titre=ticket_titre,
        )
    except RunAlreadyInProgress as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    try:
        orchestrator = await _build_orchestrator(request.project_id)
        if request.mode == "autonomous" and request.depuis_github:
            await _tirer_les_issues(request.project_id)
    except Exception as exc:
        # Rien n'a démarré : libérer le projet, sinon il resterait occupé par
        # un run qui n'existe pas.
        RUN_REGISTRY.fermer(run.run_id)
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    async def titre_getter(ticket_id: str) -> str | None:
        return await _lire_titre(ticket_svc, ticket_id)

    tache = asyncio.create_task(
        executer(
            run,
            orchestrator,
            EVENT_HUB,
            RUN_REGISTRY,
            ticket_ids=request.ticket_ids,
            max_tickets=request.max_tickets,
            titre_getter=titre_getter,
        )
    )
    _TACHES.add(tache)
    tache.add_done_callback(_TACHES.discard)
    return RunStarted(run_id=run.run_id)


async def _tirer_les_issues(project_id: str) -> int:
    """Crée les tickets manquants depuis les issues `agent-ready` du dépôt.

    Le dernier maillon de la boucle : une issue écrite sur GitHub devient un
    ticket, que le run autonome prend ensuite comme les autres. Le pull
    existait déjà — il n'était qu'un bouton à part (ticket-084).

    Un échec n'empêche pas le run : les tickets déjà là méritent de tourner.
    """
    project_path = settings.ide_workspace_dir / project_id
    project = load_project(project_path)
    if not project.github_remote or not settings.github_token:
        return 0
    agent = GithubSyncAgent(
        github_svc=GitHubService(
            token=settings.github_token, repo=project.github_remote
        ),
        ticket_svc=TicketService(project_path, project_id),
        sync_map_svc=SyncMapService(),
        project_path=project_path,
    )
    try:
        resultat = await agent.run("pull")
    except Exception as exc:  # noqa: BLE001 — voir la docstring
        _logger.warning("pull_des_issues_echoue", extra={"erreur": str(exc)})
        return 0
    return int(resultat.pulled)
