"""Assembly of the orchestrator of a run: providers per role, context, delivery, watching.

Une fonction, un orchestrateur neuf à chaque appel : rien n'est conservé d'un
appel à l'autre (ADR-008). Les refus de configuration lèvent `HTTPException`,
comme avant le déplacement : l'appelant — routeur d'orchestration ou de chat —
les rend tels quels.
"""

from fastapi import HTTPException

from tessera.config import settings
from tessera.models.ticket import TicketStatus
from tessera.services.adr import lire_contraintes
from tessera.services.agent_registry import AgentRegistryService
from tessera.services.agent_runner import OUTILS_DE_RELECTURE, AgentRunner
from tessera.services.carte_du_depot import CarteDuDepot
from tessera.services.controle_visuel import lire_le_controle
from tessera.services.documenteur_run import documenteur
from tessera.services.git_workspace import GitWorkspaceService
from tessera.services.journal_pipeline import journal_vers, journaliser_mode_rapide
from tessera.services.livreur_run import livreur
from tessera.services.orchestrator import Orchestrator
from tessera.services.pipeline_plan import ROLE_PLAN
from tessera.services.politique_run import PolitiqueRun
from tessera.services.preparation_run import preparation_du_run_declaree, tests_du_run
from tessera.services.project_loader import (
    ProjectLoader,
    load_agents_config,
    load_pipeline_config,
)
from tessera.services.providers.base import LLMProvider
from tessera.services.providers.enregistrant import ProviderEnregistrant
from tessera.services.providers.noms import ProviderInconnu
from tessera.services.providers.par_role import modele_du_role, provider_pour_role
from tessera.services.providers.refus_garde import JournalDesRefus
from tessera.services.retest_apres_rebase import retest_du_run
from tessera.services.run_recorder import RunRecorder
from tessera.services.run_worktree import RunWorktree
from tessera.services.security_auditor import SecurityAuditorService
from tessera.services.surveillance_run import (
    chercheur_pr_mergee,
    lecteur_etat_pr,
    surveillance_pour,
)
from tessera.services.test_runner import TestRunnerService
from tessera.services.ticket_service import TicketService
from tessera.services.validator import ValidatorService

_OPEN_STATUSES = {
    TicketStatus.todo,
    TicketStatus.in_progress,
    TicketStatus.in_review,
    TicketStatus.blocked,
}


def tours_du_role(role: str) -> int | None:
    """Returns the max_turns budget for a given pipeline role (ticket-297).

    The plan role must read the codebase to decide on an approach — it does not
    have the diff in its prompt. The reviewer has the diff and only needs to look
    around. Other roles get the global default (None → settings.llm_max_turns).
    """
    if role == ROLE_PLAN:
        return settings.llm_max_turns_plan
    if role == "reviewer":
        return settings.llm_max_turns_reviewer
    if role == "securite":
        # L'audit lit hors du diff (ticket-485) : budget propre (ticket-495).
        return settings.llm_max_turns_securite
    return None


async def build_project_context(project_id: str) -> str:
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

    recent_decisions = lire_contraintes(project_path / "memory")

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


async def build_orchestrator(
    project_id: str,
    wt: RunWorktree | None = None,
    chemins_absents: tuple[str, ...] = (),
    rapide: bool = False,
) -> Orchestrator:
    # Le dossier réel porte `agents.json` et la politique ; `racine_run` est
    # là où le run lit et écrit : le même dossier, ou son pendant dans le
    # worktree (ADR-056).
    project_path = settings.ide_workspace_dir / project_id
    racine_run = wt.projet if wt is not None else project_path
    # La politique du run — autonomie, racine git, artefacts, commande de
    # tests — se lit **ici**, une fois, avant le premier agent, et voyage vers
    # chaque service qui en dépend. Relue au moment d'agir, elle obéirait à ce
    # qu'un codeur aurait écrit dans `agents.json` pendant le run (ticket-119).
    politique = PolitiqueRun.lire(project_path)
    racine_ecriture = politique.racine_ecriture(project_path, worktree=wt)

    # Chaque rôle a son provider, déclaré dans le manifeste avec son repli
    # (ticket-188). Le reviewer relit : le sien est réduit à la lecture. Les
    # services texte→JSON n'ont aucun usage des outils fichier (ticket-044
    # review, finding 4).
    # `AgentRunner` enregistre lui-même les appels du codeur et du reviewer.
    # Les services sans outils — sécurité, validateur, documentation —
    # appellent le provider directement : `ProviderEnregistrant` les enregistre
    # à leur place (ticket-211). Envelopper aussi les premiers les compterait
    # deux fois.
    # Les refus du garde-fou pendant un tour, pour le reviewer et le validateur
    # (ticket-476). Un journal par orchestrateur : il ne survit pas au run.
    journal_refus = JournalDesRefus()

    def _par_role(role: str) -> LLMProvider:
        # Le plan lit comme le reviewer : il prépare le code, il ne l'écrit pas
        # (ticket-243). Chacun a son propre budget de tours (ticket-297).
        lecture = role in ("reviewer", ROLE_PLAN)
        outils = OUTILS_DE_RELECTURE if lecture else None
        inner = provider_pour_role(
            project_path, role, tools=outils, racine_ecriture=racine_ecriture,
            project_id=project_id, max_turns=tours_du_role(role),
            journal_refus=journal_refus, rapide=rapide,
        )
        return inner

    journal_repli = journal_vers(racine_run / "memory" / "pipeline-log.md")

    def _sans_outils(role: str) -> LLMProvider:
        inner = provider_pour_role(
            project_path, role, allow_tools=False, project_id=project_id,
            journal_repli=journal_repli, rapide=rapide,
        )
        return ProviderEnregistrant(inner, role=role, db_path=settings.ide_db_path)

    def _en_lecture(role: str) -> LLMProvider:
        # Lecture seule, enregistré comme `_sans_outils` : l'audit appelle le
        # provider directement, `AgentRunner` ne le compte pas (ticket-485).
        inner = provider_pour_role(
            project_path, role, tools=OUTILS_DE_RELECTURE,
            racine_ecriture=racine_ecriture, project_id=project_id,
            max_turns=tours_du_role(role), journal_repli=journal_repli,
            rapide=rapide,
        )
        return ProviderEnregistrant(inner, role=role, db_path=settings.ide_db_path)

    try:
        agent_configs = load_agents_config(project_path)
        if rapide:
            journaliser_mode_rapide(
                racine_run / "memory" / "pipeline-log.md", project_id,
                [c.role for c in agent_configs if c.active and c.fallback is not None],
            )
        provider = _par_role("codeur")
    except ProviderInconnu as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    registry = AgentRegistryService(settings.ide_prompts_dir)

    runner = AgentRunner(
        provider, registry, db_path=settings.ide_db_path, project_path=racine_run,
        provider_par_role=_par_role,
    )

    project_context = await build_project_context(project_id)
    ticket_svc = TicketService(racine_run, project_id)

    pipeline_cfg = load_pipeline_config(project_path)

    commande, env_tests = tests_du_run(politique, wt, project_path)
    test_runner = (
        TestRunnerService(
            cwd=pipeline_cfg.test_cwd, timeout=pipeline_cfg.test_timeout_s,
            env=env_tests,
        )
        if pipeline_cfg.testeur_enabled
        else None
    )
    security_auditor = (
        SecurityAuditorService(
            _en_lecture("securite"), settings.ide_prompts_dir,
            model=modele_du_role(project_path, "securite"),
            max_turns=tours_du_role("securite"),
            diff_only_provider=_sans_outils("securite"),
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

    git_workspace = GitWorkspaceService(racine_run, politique=politique, worktree=wt)

    from tessera.services.ci_watcher import CI_WATCHER

    return Orchestrator(
        journal_refus=journal_refus,
        runner=runner,
        ticket_service=ticket_svc,
        project_context=project_context,
        agent_configs=agent_configs,
        pipeline_log_path=racine_run / "memory" / "pipeline-log.md",
        max_review_rounds=pipeline_cfg.max_review_rounds,
        test_runner=test_runner,
        test_command=commande,
        security_auditor=security_auditor,
        validator=validator,
        project_path=racine_run,
        git_workspace=git_workspace,
        run_max_budget_usd=settings.run_max_budget_usd,
        # Le tracker vit sur le provider, qui est le seul à voir les
        # messages du SDK. `getattr` parce que le provider Messages API
        # n'a pas de quota d'abonnement à suivre (ticket-054).
        quota_tracker=getattr(provider, "quota", None),
        # Phase 1 seulement — rebase, push, PR. Phase 2 confiée à
        # CI_WATCHER via `surveiller` (ADR-051).
        livrer=livreur(
            project_id, runner, politique, espace=git_workspace, wt=wt,
            retest=retest_du_run(git_workspace, wt is not None, test_runner, racine_run, commande, pipeline_cfg.test_cwd),
        ),
        surveiller=surveillance_pour(
            project_id, runner, politique, espace=git_workspace, wt=wt
        ),
        ci_watcher=CI_WATCHER,
        etat_pr=lecteur_etat_pr(project_id, politique),
        pr_mergee_de_branche=chercheur_pr_mergee(project_id, politique),
        documenter=documenteur(project_id, politique, wt, rapide=rapide),
        run_recorder=RunRecorder(settings.ide_db_path),
        # Depuis la racine d'écriture, pas le dossier du projet : le projet
        # bootstrap travaille au-dessus de lui (ADR-028), et sa carte doit le
        # montrer (ticket-190).
        carte_du_depot=CarteDuDepot.depuis(racine_run, politique),
        # Pour retourner sur la branche de base après livraison (ticket-378).
        base_branch=(politique.base_branch if politique else None) or settings.github_base_branch,
        # Attendre le merge du ticket précédent avant le suivant (ticket-382).
        merge_without_ci=bool(politique and politique.merge_without_ci),
        attente_merge_max_s=settings.attente_merge_max_s,
        worktree=wt,
        depot=project_path if wt is not None else None,
        controle_visuel=lire_le_controle(project_path),
        chemins_absents=chemins_absents,
        preparation=preparation_du_run_declaree(
            politique, wt, project_path, env_tests, pipeline_cfg.test_timeout_s
        ),
    )
