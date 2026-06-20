from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from anthropic import AsyncAnthropic

from vibe_ide.config import settings
from vibe_ide.models.agent import AgentResult, AgentRunRequest
from vibe_ide.models.project import ProjectContext
from vibe_ide.models.ticket import TicketStatus
from vibe_ide.services.agent_runner import AgentRunner
from vibe_ide.services.project_loader import ProjectLoader, load_agents_config
from vibe_ide.services.ticket_service import TicketService

router = APIRouter(prefix="/agents", tags=["agents"])

_OPEN_STATUSES = {
    TicketStatus.todo,
    TicketStatus.in_progress,
    TicketStatus.in_review,
    TicketStatus.blocked,
}


def _make_runner() -> AgentRunner:
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return AgentRunner(client, settings.ide_prompts_dir)


async def _build_context(project_id: str) -> ProjectContext:
    """Charge le contexte complet d'un projet pour les agents."""
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

    return ProjectContext(
        project_id=project_id,
        claude_md=project.raw_claude_md,
        active_agents=project.active_agents,
        agent_configs=load_agents_config(project_path),
        open_tickets=open_tickets,
        recent_decisions=recent_decisions,
    )


def _format_context(ctx: ProjectContext) -> str:
    tickets_summary = (
        "\n".join(f"- [{t.id}] {t.title} ({t.status.value})" for t in ctx.open_tickets)
        or "_Aucun ticket ouvert._"
    )
    return (
        f"# {ctx.project_id}\n\n"
        f"## CLAUDE.md\n{ctx.claude_md}\n\n"
        f"## Agents actifs\n{', '.join(ctx.active_agents)}\n\n"
        f"## Tickets ouverts\n{tickets_summary}\n\n"
        f"## Décisions récentes\n{ctx.recent_decisions or '_Aucune décision._'}"
    )


@router.post("/run", response_model=AgentResult)
async def run_agent(request: AgentRunRequest) -> AgentResult:
    ctx = await _build_context(request.project_id)

    ticket_svc = TicketService(
        settings.ide_workspace_dir / request.project_id, request.project_id
    )
    ticket = await ticket_svc.get_ticket(request.ticket_id)
    if ticket is None:
        raise HTTPException(
            status_code=404, detail=f"Ticket {request.ticket_id} introuvable"
        )

    agent_cfg = next(
        (c for c in ctx.agent_configs if c.role == request.role.value), None
    )

    return await _make_runner().run(
        role=request.role,
        ticket=ticket,
        project_context=_format_context(ctx),
        agent_config=agent_cfg,
    )


@router.websocket("/stream")
async def stream_agent(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        raw = await websocket.receive_json()
        request = AgentRunRequest(**raw)

        ctx = await _build_context(request.project_id)

        ticket_svc = TicketService(
            settings.ide_workspace_dir / request.project_id, request.project_id
        )
        ticket = await ticket_svc.get_ticket(request.ticket_id)
        if ticket is None:
            await websocket.send_json(
                {"error": f"Ticket {request.ticket_id} introuvable"}
            )
            return

        agent_cfg = next(
            (c for c in ctx.agent_configs if c.role == request.role.value), None
        )

        async def send_token(token: str) -> None:
            await websocket.send_text(token)

        result = await _make_runner().run(
            role=request.role,
            ticket=ticket,
            project_context=_format_context(ctx),
            agent_config=agent_cfg,
            stream_callback=send_token,
        )
        await websocket.send_json(result.model_dump())

    except WebSocketDisconnect:
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
