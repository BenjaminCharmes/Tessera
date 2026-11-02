"""Removing a project from the IDE — ticket-063, ticket-689."""

from fastapi import HTTPException, Query
from pydantic import BaseModel

from tessera.config import settings
from tessera.routers.projects.shared import new_router, require_project_path
from tessera.services.project_removal import (
    RemovalError,
    delete_project,
    describe_removal,
    detach_project,
)

router = new_router()


class RemovalPlanResponse(BaseModel):
    project_id: str
    #: Le chemin réellement visé, liens résolus : c'est lui qu'il faut montrer
    #: avant de décider.
    real_path: str
    is_symlink: bool
    unpushed_commits: int


class DetachResponse(BaseModel):
    detached: bool
    #: Où les fichiers ont été déplacés, ou le lien retiré.
    moved_to: str


@router.get("/{project_id}/removal-plan", response_model=RemovalPlanResponse)
async def get_removal_plan(project_id: str) -> RemovalPlanResponse:
    """Décrit ce qu'un retrait toucherait, sans rien modifier."""
    plan = await describe_removal(require_project_path(project_id))
    return RemovalPlanResponse(
        project_id=plan.project_id,
        real_path=plan.real_path,
        is_symlink=plan.is_symlink,
        unpushed_commits=plan.unpushed_commits,
    )


@router.post("/{project_id}/detach", response_model=DetachResponse)
async def detach(project_id: str) -> DetachResponse:
    """Retire le projet de l'IDE. Les fichiers restent."""
    try:
        moved_to = await detach_project(require_project_path(project_id))
    except RemovalError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return DetachResponse(detached=True, moved_to=moved_to)


@router.delete("/{project_id}", status_code=204)
async def delete(project_id: str, confirmed: bool = Query(default=False)) -> None:
    """Efface définitivement un projet. Ne franchit jamais un lien symbolique."""
    project_path = require_project_path(project_id)
    try:
        await delete_project(
            project_path, confirmed=confirmed, workspace=settings.ide_workspace_dir
        )
    except RemovalError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
