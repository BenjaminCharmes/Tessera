from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from vibe_ide.config import settings
from vibe_ide.models.ticket import TicketStatus
from vibe_ide.services.agent_registry import AgentRegistryService
from vibe_ide.services.agent_runner import AgentRunner
from vibe_ide.services.database import create_run, finish_run, save_event
from vibe_ide.services.doc_updater import DocUpdaterService
from vibe_ide.services.git_workspace import GitWorkspaceService
from vibe_ide.services.providers import get_provider
from vibe_ide.services.security_auditor import SecurityAuditorService
from vibe_ide.services.test_runner import TestRunnerService
from vibe_ide.services.validator import ValidatorService
from vibe_ide.services.orchestrator import (
    Orchestrator,
    OrchestratorEvent,
    PipelineResult,
)
from vibe_ide.services.project_loader import ProjectLoader, load_agents_config, load_pipeline_config
from vibe_ide.services.ticket_service import TicketService

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])

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
    # doc_updater) have no use for file/shell tools — doc_updater writes
    # files itself via `_write_files`, never through an SDK tool, and no cwd
    # is threaded to it. Give them all a tool-less provider (ticket-044
    # review, finding 4; doc_updater moved here per merge-gate finding 2).
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

    doc_updater = (
        DocUpdaterService(tool_less_provider, settings.ide_prompts_dir)
        if pipeline_cfg.doc_updater_enabled
        else None
    )
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
        doc_updater=doc_updater,
        test_runner=test_runner,
        test_command=pipeline_cfg.test_command,
        security_auditor=security_auditor,
        validator=validator,
        project_path=project_path,
        git_workspace=git_workspace,
    )


@router.post("/run", response_model=PipelineResult)
async def run_pipeline(request: RunRequest) -> PipelineResult:
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


@router.post("/run-autonomous", response_model=list[PipelineResult])
async def run_autonomous(request: RunAutonomousRequest) -> list[PipelineResult]:
    orchestrator = await _build_orchestrator(request.project_id)
    return await orchestrator.run_autonomous(request.project_id, request.max_tickets)


@router.websocket("/stream/{project_id}")
async def stream_pipeline(websocket: WebSocket, project_id: str) -> None:
    await websocket.accept()
    try:
        raw = await websocket.receive_json()
        orchestrator = await _build_orchestrator(project_id)

        ticket_id: str | None = raw.get("ticket_id")
        mode: str = raw.get("mode", "single")

        if mode == "autonomous":
            async def send_event_autonomous(event: OrchestratorEvent) -> None:
                await websocket.send_text(event.model_dump_json())

            max_tickets = int(raw.get("max_tickets", 5))
            await orchestrator.run_autonomous(project_id, max_tickets, send_event_autonomous)
        elif ticket_id:
            run_id = await create_run(settings.ide_db_path, project_id, ticket_id)

            async def send_event(event: OrchestratorEvent) -> None:
                await websocket.send_text(event.model_dump_json())
                await save_event(
                    settings.ide_db_path,
                    run_id,
                    event.type.value,
                    event.agent.value if event.agent else None,
                    event.data,
                    event.timestamp.isoformat(),
                )

            try:
                result = await orchestrator.run_pipeline(project_id, ticket_id, send_event, run_id=run_id)
                await finish_run(
                    settings.ide_db_path,
                    run_id,
                    result.rounds,
                    result.approved,
                    result.final_status.value,
                )
            except ValueError as exc:
                await websocket.send_json({"error": str(exc)})
        else:
            await websocket.send_json({"error": "ticket_id ou mode=autonomous requis"})

    except WebSocketDisconnect:
        pass
    except HTTPException as exc:
        try:
            await websocket.send_json({"error": exc.detail})
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
