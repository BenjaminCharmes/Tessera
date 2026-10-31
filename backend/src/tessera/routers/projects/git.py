"""Git link of a project: status, init, remote — ticket-061, ticket-689."""

import re

from fastapi import HTTPException
from pydantic import BaseModel

from tessera.config import settings
from tessera.routers.projects.shared import new_router, require_project_path
from tessera.services.git_link import (
    GitLinkError,
    RemoteNotEmpty,
    git_status,
    init_repository,
    link_remote,
)
from tessera.services.github_service import GitHubService
from tessera.services.politique_run import PolitiqueRun

router = new_router()


class GitStatusResponse(BaseModel):
    is_repository: bool
    has_commits: bool
    remote_url: str | None = None
    # Renseigné quand le projet vit dans un dépôt qui n'est pas le sien :
    # `init` créera alors bien son propre dépôt (ticket-061).
    nested_in: str | None = None
    # Le projet déclare `git_root: ancestor` : travailler dans le dépôt qui le
    # contient est son mode normal (ADR-028), pas une anomalie à corriger.
    # Sans ce champ, l'écran annonçait « ce projet n'est pas versionné » et
    # proposait d'imbriquer un dépôt dans celui de Tessera (ticket-171).
    uses_parent_repository: bool = False


class LinkRemoteRequest(BaseModel):
    repo_url: str
    # L'utilisateur confirme les deux cas qu'il est seul à pouvoir trancher :
    # un dépôt distant non vide, et un `origin` déjà configuré.
    confirmed: bool = False


def _repo_slug(repo_url: str) -> str | None:
    """Extrait `owner/repo` d'une URL GitHub, pour interroger l'API."""
    match = re.search(r"github\.com[:/]([\w.\-]+/[\w.\-]+?)(?:\.git)?/?$", repo_url.strip())
    return match.group(1) if match else None


@router.get("/{project_id}/git/status", response_model=GitStatusResponse)
async def get_git_status(project_id: str) -> GitStatusResponse:
    chemin = require_project_path(project_id)
    status = await git_status(chemin)
    return GitStatusResponse(
        is_repository=status.is_own_repository,
        has_commits=status.has_commits,
        remote_url=status.remote_url,
        nested_in=status.is_nested_in,
        uses_parent_repository=PolitiqueRun.lire(chemin).dans_le_depot_parent,
    )


@router.post("/{project_id}/git/init", response_model=GitStatusResponse)
async def init_git(project_id: str) -> GitStatusResponse:
    """Initialise un dépôt dans le projet. Sans effet s'il en a déjà un.

    Refusé sur un projet en `git_root: ancestor` : il travaille dans le dépôt
    qui le contient (ADR-028), et l'initialiser en imbriquerait un second —
    ce qu'ADR-024 existe pour empêcher. Le refus est ici et pas seulement à
    l'écran : une garde qui dépend de l'interface n'en est pas une (ADR-027).
    """
    chemin = require_project_path(project_id)
    if PolitiqueRun.lire(chemin).dans_le_depot_parent:
        raise HTTPException(
            status_code=422,
            detail=(
                "Ce projet déclare `git_root: ancestor` : il travaille dans le "
                "dépôt qui le contient. Initialiser un dépôt ici en imbriquerait "
                "un second. Retire `git_root` de son agents.json pour lui en "
                "donner un propre."
            ),
        )
    try:
        status = await init_repository(chemin)
    except GitLinkError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return GitStatusResponse(
        is_repository=status.is_own_repository,
        has_commits=status.has_commits,
        remote_url=status.remote_url,
        nested_in=status.is_nested_in,
    )


@router.post("/{project_id}/git/link", response_model=GitStatusResponse)
async def link_git_remote(project_id: str, body: LinkRemoteRequest) -> GitStatusResponse:
    """Attache un remote GitHub au projet, après vérification du dépôt distant."""
    project_path = require_project_path(project_id)

    # Le dépôt distant n'est interrogé que si un token le permet. Sans token,
    # on ne peut rien affirmer : on exige alors une confirmation explicite
    # plutôt que de supposer le dépôt vide.
    remote_is_empty = body.confirmed
    slug = _repo_slug(body.repo_url)
    if settings.github_token and slug:
        info = await GitHubService(token=settings.github_token, repo=slug).get_repository_info()
        if not info.exists:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Le dépôt '{slug}' est introuvable, ou le GITHUB_TOKEN "
                    "configuré n'y a pas accès."
                ),
            )
        remote_is_empty = info.is_empty

    try:
        status = await link_remote(
            project_path,
            body.repo_url,
            remote_is_empty=remote_is_empty,
            confirmed=body.confirmed,
        )
    except RemoteNotEmpty as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except GitLinkError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return GitStatusResponse(
        is_repository=status.is_own_repository,
        has_commits=status.has_commits,
        remote_url=status.remote_url,
        nested_in=status.is_nested_in,
    )
