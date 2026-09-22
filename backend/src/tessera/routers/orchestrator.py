from collections.abc import Awaitable, Callable

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from tessera.config import settings
from tessera.models.ticket import TicketStatus
from tessera.agents.github_sync import GithubSyncAgent
from tessera.services.agent_registry import AgentRegistryService
from tessera.services.sync_map import SyncMapService
from tessera.services.agent_runner import AgentRunner
from tessera.services.documentation import DocumentationService
from tessera.routers.pipeline_stream import libelle_du_run, stream_verrouille
from tessera.services.database import create_run, finish_run, save_event
from tessera.services.git_workspace import GitWorkspaceService
from tessera.services.github_service import GitHubService
from tessera.services.github_workflow import GitHubWorkflowService
from tessera.services.livraison import Livraison, LivraisonService
from tessera.services.providers import get_provider
from tessera.services.resolveur_conflit import ResolveurConflitService
from tessera.services.run_lock import RUN_LOCK, RunAlreadyInProgress
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

_OPEN_STATUSES = {
    TicketStatus.todo,
    TicketStatus.in_progress,
    TicketStatus.in_review,
    TicketStatus.blocked,
}


class RunRequest(BaseModel):
    project_id: str
    ticket_id: str


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
    provider = get_provider(
        settings.llm_provider, settings.anthropic_api_key,
        max_turns=settings.llm_max_turns, max_budget_usd=settings.llm_max_budget_usd,
    )
    # Pure text-in/JSON-out services (security_auditor, validator,
    # documentation) have no use for file/shell tools — they write
    # files itself via `_write_files`, never through an SDK tool, and no cwd
    # is threaded to it. Give them all a tool-less provider (ticket-044
    # review, finding 4).
    tool_less_provider = get_provider(
        settings.llm_provider, settings.anthropic_api_key,
        max_turns=settings.llm_max_turns, max_budget_usd=settings.llm_max_budget_usd,
        allow_tools=False,
    )
    registry = AgentRegistryService(settings.ide_prompts_dir)
    project_path = settings.ide_workspace_dir / project_id
    runner = AgentRunner(
        provider, registry, db_path=settings.ide_db_path, project_path=project_path
    )

    project_context = await _build_project_context(project_id)
    ticket_svc = TicketService(project_path, project_id)

    agent_configs = load_agents_config(project_path)
    pipeline_cfg = load_pipeline_config(project_path)

    test_runner = TestRunnerService() if pipeline_cfg.testeur_enabled else None
    security_auditor = (
        SecurityAuditorService(tool_less_provider, settings.ide_prompts_dir)
        if pipeline_cfg.securite_enabled
        else None
    )
    validator = (
        ValidatorService(tool_less_provider, settings.ide_prompts_dir)
        if pipeline_cfg.validateur_enabled
        else None
    )

    git_workspace = GitWorkspaceService(project_path)

    return Orchestrator(
        runner=runner,
        ticket_service=ticket_svc,
        project_context=project_context,
        agent_configs=agent_configs,
        pipeline_log_path=project_path / "memory" / "pipeline-log.md",
        max_review_rounds=pipeline_cfg.max_review_rounds,
        test_runner=test_runner,
        test_command=pipeline_cfg.test_command,
        security_auditor=security_auditor,
        validator=validator,
        project_path=project_path,
        git_workspace=git_workspace,
        run_max_budget_usd=settings.run_max_budget_usd,
        # Le tracker vit sur le provider, qui est le seul à voir les
        # messages du SDK. `getattr` parce que le provider Messages API
        # n'a pas de quota d'abonnement à suivre (ticket-054).
        quota_tracker=getattr(provider, "quota", None),
        livrer=_livreur(project_id, runner),
        documenter=_documenteur(project_id),
        run_recorder=RunRecorder(settings.ide_db_path),
    )


def _documenteur(project_id: str) -> Callable[[], Awaitable[None]]:
    """Fabrique la mise à jour de documentation d'un projet (ticket-092).

    Appelée **une fois par lot**, pas par ticket : la documentation décrit le
    produit, pas un changement. Sans outils — elle lit des tickets et rend du
    JSON, elle n'a aucune raison d'écrire elle-même sur le disque.
    """
    project_path = settings.ide_workspace_dir / project_id
    service = DocumentationService(
        get_provider(
            settings.llm_provider, settings.anthropic_api_key, allow_tools=False
        ),
        settings.ide_prompts_dir,
    )

    async def documenter() -> None:
        resultat = await service.mettre_a_jour(project_path)
        if resultat.fichiers_modifies:
            _logger.info(
                "documentation_mise_a_jour",
                extra={"fichiers": resultat.fichiers_modifies},
            )
        for refus in resultat.refus:
            _logger.warning("documentation_refusee", extra={"motif": refus})

    return documenter


def _livreur(
    project_id: str, runner: AgentRunner | None = None
) -> Callable[[PipelineResult], Awaitable[Livraison]]:
    """Fabrique la livraison d'un projet, telle que l'orchestrateur l'appelle.

    Branchée sur l'orchestrateur plutôt qu'appelée par chaque endpoint : les
    trois modes de run — unique, file, autonome — passent par `run_pipeline`,
    et n'en brancher qu'un réservait la livraison au cas où l'utilisateur est
    déjà devant son écran (ticket-084).

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

    service = LivraisonService(
        git_workspace=GitWorkspaceService(project_path),
        workflow=GitHubWorkflowService(
            git_workspace=GitWorkspaceService(project_path),
            github=github,
            base_branch=settings.github_base_branch,
            project_path=project_path,
        ),
        project_path=project_path,
        base_branch=settings.github_base_branch,
        # Sans runner — appel programmatique, test — pas de résolveur : le
        # conflit annule le rebase et remonte, comme avant ticket-090.
        resolveur=(
            ResolveurConflitService(runner, project_path).resoudre
            if runner is not None
            else None
        ),
    )

    ticket_svc = TicketService(project_path, project_id)

    async def livrer(result: PipelineResult) -> Livraison:
        ticket = await ticket_svc.get_ticket(result.ticket_id)
        try:
            return await service.livrer(
                ticket_id=result.ticket_id,
                ticket_title=ticket.title if ticket else result.ticket_id,
                ticket_body=ticket.body if ticket else "",
                branch=result.branch,
                approuve=result.approved,
            )
        except Exception as exc:  # noqa: BLE001 — voir la docstring
            _logger.warning("livraison_echouee", extra={"erreur": str(exc)})
            return Livraison(arret=f"Livraison interrompue : {exc}")

    return livrer


@router.post("/run", response_model=PipelineResult)
async def run_pipeline(request: RunRequest) -> PipelineResult:
    # Le verrou est pris AVANT de construire l'orchestrateur : un refus doit
    # être immédiat et bon marché. Deux runs sur le même projet passaient
    # tous deux `ensure_clean_tree`, puis le second `create_branch` faisait un
    # checkout sous le premier codeur (ticket-121).
    try:
        async with _RUN_LOCK.acquire(request.project_id, request.ticket_id):
            return await _run_un_ticket(request)
    except RunAlreadyInProgress as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


async def _run_un_ticket(request: RunRequest) -> PipelineResult:
    orchestrator = await _build_orchestrator(request.project_id)
    run_id = await create_run(settings.ide_db_path, request.project_id, request.ticket_id)

    async def on_event(event: OrchestratorEvent) -> None:
        await save_event(
            settings.ide_db_path,
            run_id,
            event.type.value,
            event.agent.value if event.agent else None,
            event.data,
            event.timestamp.isoformat(),
        )

    try:
        result = await orchestrator.run_pipeline(
            request.project_id, request.ticket_id, on_event, run_id=run_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    await finish_run(
        settings.ide_db_path,
        run_id,
        result.rounds,
        result.approved,
        result.final_status.value,
    )
    return result


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


@router.post("/run-autonomous", response_model=list[PipelineResult])
async def run_autonomous(request: RunAutonomousRequest) -> list[PipelineResult]:
    try:
        async with _RUN_LOCK.acquire(request.project_id, "run autonome"):
            if request.depuis_github:
                await _tirer_les_issues(request.project_id)
            orchestrator = await _build_orchestrator(request.project_id)
            return await orchestrator.run_autonomous(
                request.project_id, request.max_tickets
            )
    except RunAlreadyInProgress as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.websocket("/stream/{project_id}")
async def stream_pipeline(websocket: WebSocket, project_id: str) -> None:
    await websocket.accept()
    try:
        raw = await websocket.receive_json()
        async with _RUN_LOCK.acquire(project_id, libelle_du_run(raw)):
            await stream_verrouille(
                websocket,
                project_id,
                raw,
                construire=_build_orchestrator,
                tirer_les_issues=_tirer_les_issues,
            )
    except WebSocketDisconnect:
        pass
    except (HTTPException, RunAlreadyInProgress) as exc:
        try:
            detail = exc.detail if isinstance(exc, HTTPException) else str(exc)
            await websocket.send_json({"error": detail})
        except Exception:
            pass
    except Exception as exc:
        try:
            await websocket.send_json({"error": str(exc)})
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
