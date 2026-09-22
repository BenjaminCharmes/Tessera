import time

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from tessera.agents.github_sync import GithubSyncAgent
from tessera.config import settings
from tessera.models.agent import AgentResult, AgentRole, AgentRunRequest, CreateAgentConversationResponse
from tessera.models.project import ConversationMessage, CreateProjectRequest, CreateProjectResponse, ProjectContext
from tessera.models.ticket import TicketStatus
from tessera.services.agent_creator import AgentCreatorService
from tessera.services.agent_registry import AgentRegistryService
from tessera.services.agent_runner import AgentRunner
from tessera.services.github_service import GitHubService
from tessera.services.project_creator import ProjectCreatorService
from tessera.services.providers import get_provider
from tessera.services.providers.base import LLMProvider
from tessera.services.project_loader import ProjectLoader, load_agents_config
from tessera.services.sync_map import SyncMapService
from tessera.services.ticket_service import TicketService

router = APIRouter(prefix="/agents", tags=["agents"])

_OPEN_STATUSES = {
    TicketStatus.todo,
    TicketStatus.in_progress,
    TicketStatus.in_review,
    TicketStatus.blocked,
}


def _make_runner(project_id: str) -> AgentRunner:
    provider = get_provider(
        settings.llm_provider, settings.anthropic_api_key,
        max_turns=settings.llm_max_turns, max_budget_usd=settings.llm_max_budget_usd,
    )
    registry = AgentRegistryService(settings.ide_prompts_dir)
    project_path = settings.ide_workspace_dir / project_id
    return AgentRunner(
        provider, registry, project_path=project_path, fabrique_provider=_provider_limite
    )


def _provider_limite(outils: list[str]) -> LLMProvider:
    """Le même provider, réduit aux outils nommés — le reviewer ne lit que."""
    return get_provider(
        settings.llm_provider, settings.anthropic_api_key,
        max_turns=settings.llm_max_turns, max_budget_usd=settings.llm_max_budget_usd,
        tools=outils,
    )


def _make_project_creator() -> ProjectCreatorService:
    # Pure text-in/JSON-out: ProjectCreatorService writes files itself via
    # ProjectLoader, never through an SDK tool, and no cwd is threaded to it
    # here (ticket-044 merge-gate review, finding 2).
    provider = get_provider(
        settings.llm_provider, settings.anthropic_api_key,
        max_turns=settings.llm_max_turns, max_budget_usd=settings.llm_max_budget_usd,
        allow_tools=False,
    )
    return ProjectCreatorService(provider, settings.ide_prompts_dir, settings.ide_workspace_dir)


def _make_agent_creator() -> AgentCreatorService:
    # Pure text-in/JSON-out: no filesystem tools needed (ticket-044 review, finding 4).
    provider = get_provider(
        settings.llm_provider, settings.anthropic_api_key,
        max_turns=settings.llm_max_turns, max_budget_usd=settings.llm_max_budget_usd,
        allow_tools=False,
    )
    return AgentCreatorService(provider, settings.ide_prompts_dir)


class CreateAgentRequest(BaseModel):
    conversation: list[ConversationMessage]


async def _build_context(project_id: str) -> ProjectContext:
    """Loads the full context of a project for agents."""
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


async def _run_github_sync(project_id: str) -> AgentResult:
    if not settings.github_token or not settings.github_repo:
        raise HTTPException(
            status_code=400,
            detail="GITHUB_TOKEN et GITHUB_REPO doivent être configurés",
        )
    t0 = time.monotonic()
    project_path = settings.ide_workspace_dir / project_id
    ticket_svc = TicketService(project_path, project_id)
    github_svc = GitHubService(token=settings.github_token, repo=settings.github_repo)
    sync_map_svc = SyncMapService()
    agent = GithubSyncAgent(
        github_svc=github_svc,
        ticket_svc=ticket_svc,
        sync_map_svc=sync_map_svc,
        project_path=project_path,
    )
    result = await agent.run("pull")
    duration_ms = int((time.monotonic() - t0) * 1000)

    summary = f"github-sync: {result.pulled} ticket(s) créé(s), {result.skipped} ignoré(s)."
    return AgentResult(
        role=AgentRole.github_sync,
        ticket_id="*",
        content=summary,
        suggested_status=TicketStatus.done,
        created_tickets=[],
        duration_ms=duration_ms,
    )


@router.post("/create-project", response_model=CreateProjectResponse)
async def create_project(request: CreateProjectRequest) -> CreateProjectResponse:
    try:
        return await _make_project_creator().create_project(request.conversation)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/create-agent", response_model=CreateAgentConversationResponse)
async def create_agent(request: CreateAgentRequest) -> CreateAgentConversationResponse:
    return await _make_agent_creator().create_agent(request.conversation)


@router.post("/run", response_model=AgentResult)
async def run_agent(request: AgentRunRequest) -> AgentResult:
    if request.role == AgentRole.github_sync:
        return await _run_github_sync(request.project_id)

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
        (c for c in ctx.agent_configs if c.role == request.role), None
    )

    return await _make_runner(request.project_id).run(
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
            (c for c in ctx.agent_configs if c.role == request.role), None
        )

        async def send_token(token: str) -> None:
            await websocket.send_text(token)

        result = await _make_runner(request.project_id).run(
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
