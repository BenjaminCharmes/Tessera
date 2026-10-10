"""Shared FastAPI route dependencies — ticket-370."""
from fastapi import HTTPException
from starlette.requests import Request

from tessera.utils.project_id import validate_project_id


async def require_valid_project_id(request: Request) -> None:
    """Validate the ``{project_id}`` path parameter before any disk access.

    Silently skipped for routes that have no ``project_id`` path parameter.
    Invalid identifiers raise 404 without reading anything from the filesystem.
    """
    project_id: str | None = request.path_params.get("project_id")
    if project_id is None:
        return
    if not validate_project_id(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
