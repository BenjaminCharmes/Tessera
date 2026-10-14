"""Capture a project's screens and serve the images — ticket-432."""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from tessera.config import settings
from tessera.routers.dependencies import require_valid_project_id
from tessera.services import captures
from tessera.services.captures_config import load_captures_config

router = APIRouter(
    prefix="/projects",
    tags=["captures"],
    dependencies=[Depends(require_valid_project_id)],
)


def _racine(project_id: str) -> Path:
    racine = settings.ide_workspace_dir / project_id
    if not racine.is_dir():
        raise HTTPException(status_code=404, detail=f"Projet inconnu : {project_id}")
    return racine


@router.post("/{project_id}/captures")
async def prendre_les_captures(project_id: str) -> dict[str, list[str]]:
    config = load_captures_config(_racine(project_id))
    if config is None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Le projet « {project_id} » ne déclare aucune capture. Ajoute "
                "une section `captures` dans son `agents.json` : "
                '{"url": "http://localhost:5196", "ecrans": '
                '[{"nom": "accueil", "chemin": "/"}]}.'
            ),
        )
    if not await captures.app_repond(config.url):
        raise HTTPException(
            status_code=409,
            detail=(
                f"L'app du projet « {project_id} » ne répond pas à {config.url}. "
                "Lance-la d'abord, puis recommence."
            ),
        )
    try:
        noms = await captures.capturer(project_id, config)
    except captures.CapturesEchouees as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"captures": noms}


@router.get("/{project_id}/captures/{fichier}")
async def servir_une_capture(project_id: str, fichier: str) -> FileResponse:
    _racine(project_id)
    # Le motif seul exclut `..`, `/` et `\` : pas de traversée de chemin.
    chemin = captures.dossier_des_captures(project_id) / fichier
    if not captures.MOTIF_FICHIER.fullmatch(fichier) or not chemin.is_file():
        raise HTTPException(status_code=404, detail="Capture inconnue")
    return FileResponse(chemin, media_type="image/png")
