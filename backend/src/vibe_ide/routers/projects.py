from fastapi import APIRouter

from vibe_ide.models.project import Project
from vibe_ide.models.ticket import Ticket

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[Project])
async def list_projects() -> list[Project]:
    return []


@router.post("", response_model=Project, status_code=201)
async def create_project(project: Project) -> Project:
    return project


@router.get("/{project_id}/tickets/archive", response_model=list[Ticket])
async def list_archived_tickets(project_id: str) -> list[Ticket]:
    return []
