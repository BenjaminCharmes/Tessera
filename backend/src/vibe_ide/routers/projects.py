from fastapi import APIRouter, HTTPException, Query

from vibe_ide.config import settings
from vibe_ide.models.project import Project, ProjectContext, ProjectCreate
from vibe_ide.models.ticket import TicketStatus
from vibe_ide.services.database import PipelineRunSummary, list_runs
from vibe_ide.services.project_loader import ProjectLoader, load_agents_config
from vibe_ide.services.ticket_service import TicketService

router = APIRouter(prefix="/projects", tags=["projects"])

_OPEN_STATUSES = {TicketStatus.todo, TicketStatus.in_progress, TicketStatus.in_review, TicketStatus.blocked}


def _loader() -> ProjectLoader:
    return ProjectLoader(settings.ide_workspace_dir)


def _ticket_svc(project_id: str) -> TicketService:
    return TicketService(settings.ide_workspace_dir / project_id, project_id)


@router.get("", response_model=list[Project])
async def list_projects() -> list[Project]:
    return await _loader().list_projects()


@router.post("", response_model=Project, status_code=201)
async def create_project(body: ProjectCreate) -> Project:
    try:
        return await _loader().create_project(body)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


# Note : les routes avec sous-chemin spécifique doivent être avant /{project_id}
@router.get("/{project_id}/runs", response_model=list[PipelineRunSummary])
async def list_project_runs(
    project_id: str,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[PipelineRunSummary]:
    rows = await list_runs(settings.ide_db_path, project_id, limit)
    return [PipelineRunSummary(**row) for row in rows]


@router.get("/{project_id}/context", response_model=ProjectContext)
async def get_project_context(project_id: str) -> ProjectContext:
    try:
        project = await _loader().load_project(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    project_path = settings.ide_workspace_dir / project_id
    all_tickets = await _ticket_svc(project_id).list_tickets()
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


@router.get("/{project_id}", response_model=Project)
async def get_project(project_id: str) -> Project:
    try:
        return await _loader().load_project(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
