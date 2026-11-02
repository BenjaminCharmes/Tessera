"""Artifact mode of a project — ticket-062, ticket-689."""

from pydantic import BaseModel

from tessera.routers.projects.shared import new_router, require_project_path
from tessera.services.artifacts import (
    ArtifactMode,
    apply_artifact_mode,
    read_artifact_mode,
    tracked_artifact_paths,
)

router = new_router()


class ArtifactModeResponse(BaseModel):
    mode: ArtifactMode
    #: Artefacts déjà dans l'index git. Passer en `local` ne les en sort pas :
    #: git continue de suivre ce qu'il suit déjà.
    already_tracked: list[str] = []


class SetArtifactModeRequest(BaseModel):
    mode: ArtifactMode


@router.get("/{project_id}/artifacts", response_model=ArtifactModeResponse)
async def get_artifact_mode(project_id: str) -> ArtifactModeResponse:
    project_path = require_project_path(project_id)
    return ArtifactModeResponse(
        mode=read_artifact_mode(project_path),
        already_tracked=await tracked_artifact_paths(project_path),
    )


@router.put("/{project_id}/artifacts", response_model=ArtifactModeResponse)
async def set_artifact_mode(
    project_id: str, body: SetArtifactModeRequest
) -> ArtifactModeResponse:
    """Choisit si les artefacts Tessera partent dans le dépôt du projet.

    L'exclusion passe par `.git/info/exclude`, jamais par `.gitignore` : ce
    dernier est versionné, donc le modifier annoncerait dans un diff ce qu'on
    voulait justement garder hors du dépôt.

    Les fichiers **déjà suivis** sont signalés, pas retirés : les sortir de
    l'index est un `git rm --cached`, qui se décide.
    """
    project_path = require_project_path(project_id)
    await apply_artifact_mode(project_path, body.mode)
    return ArtifactModeResponse(
        mode=body.mode,
        already_tracked=await tracked_artifact_paths(project_path),
    )
