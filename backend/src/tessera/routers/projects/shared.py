"""Helpers shared by the project routes — ticket-689."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from tessera.config import settings
from tessera.routers.dependencies import require_valid_project_id
from tessera.services.project_loader import ProjectLoader
from tessera.services.ticket_service import TicketService


def new_router() -> APIRouter:
    """A router on `/projects` that validates `{project_id}` before any disk access."""
    return APIRouter(
        prefix="/projects",
        tags=["projects"],
        dependencies=[Depends(require_valid_project_id)],
    )


def loader() -> ProjectLoader:
    return ProjectLoader(settings.ide_workspace_dir)


def ticket_svc(project_id: str) -> TicketService:
    return TicketService(settings.ide_workspace_dir / project_id, project_id)


def require_project_path(project_id: str) -> Path:
    project_path = settings.ide_workspace_dir / project_id
    if not project_path.is_dir():
        raise HTTPException(status_code=404, detail=f"Projet introuvable : {project_id}")
    return project_path
