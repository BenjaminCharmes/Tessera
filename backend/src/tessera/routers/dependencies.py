"""Shared FastAPI route dependencies — ticket-370."""
from fastapi import HTTPException
from starlette.requests import Request

from tessera.config import settings
from tessera.services.github.github_service import GitHubService
from tessera.utils.project_id import validate_project_id


def require_github_service(github_remote: str | None) -> GitHubService:
    """Build the GitHub service of a project, or refuse with a 422.

    Shared by the routers that open or read pull requests: the project must
    declare a ``github_remote`` and Tessera must hold a ``GITHUB_TOKEN``.
    """
    if not github_remote:
        raise HTTPException(
            status_code=422,
            detail="Ce projet n'a pas de github_remote configuré dans agents.json.",
        )
    if not settings.github_token:
        raise HTTPException(
            status_code=422,
            detail="GITHUB_TOKEN non configuré dans les settings.",
        )
    return GitHubService(token=settings.github_token, repo=github_remote)


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
