from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from anthropic import AsyncAnthropic

from vibe_ide.config import settings
from vibe_ide.models.ticket import TicketStatus
from vibe_ide.services.agent_runner import AgentRunner
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


async def _build_orchestrator(project_id: str) -> Orchestrator:
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    runner = AgentRunner(client, settings.ide_prompts_dir)

    loader = ProjectLoader(settings.ide_workspace_dir)
    try:
        project = await loader.load_project(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    project_path = settings.ide_workspace_dir / project_id
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
    project_context = (
        f"# {project_id}\n\n"
        f"## CLAUDE.md\n{project.raw_claude_md}\n\n"
        f"## Agents actifs\n{', '.join(project.active_agents)}\n\n"
        f"## Tickets ouverts\n{tickets_summary}\n\n"
        f"## Décisions récentes\n{recent_decisions or '_Aucune décision._'}"
    )

    agent_configs = load_agents_config(project_path)
    pipeline_cfg = load_pipeline_config(project_path)

    return Orchestrator(
        runner=runner,
        ticket_service=ticket_svc,
        project_context=project_context,
        agent_configs=agent_configs,
        pipeline_log_path=project_path / "memory" / "pipeline-log.md",
        max_review_rounds=pipeline_cfg.max_review_rounds,
    )


@router.post("/run", response_model=PipelineResult)
async def run_pipeline(request: RunRequest) -> PipelineResult:
    orchestrator = await _build_orchestrator(request.project_id)

    async def noop(event: OrchestratorEvent) -> None:
        pass

    try:
        return await orchestrator.run_pipeline(request.project_id, request.ticket_id, noop)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


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

        async def send_event(event: OrchestratorEvent) -> None:
            await websocket.send_text(event.model_dump_json())

        ticket_id: str | None = raw.get("ticket_id")
        mode: str = raw.get("mode", "single")

        if mode == "autonomous":
            max_tickets = int(raw.get("max_tickets", 5))
            await orchestrator.run_autonomous(project_id, max_tickets, send_event)
        elif ticket_id:
            try:
                await orchestrator.run_pipeline(project_id, ticket_id, send_event)
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
