"""Capture a project's screens and serve the images — ticket-432."""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from tessera.config import settings
from tessera.routers.dependencies import require_valid_project_id
from tessera.services import captures
from tessera.services.captures_config import ConfigCaptures, load_captures_config
from tessera.services.captures_session import lire_le_jeton

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


def _jeton(project_id: str, config: ConfigCaptures) -> str | None:
    """Read the session token, or refuse with a 409 that names where to put it."""
    if config.session is None:
        return None
    jeton = lire_le_jeton(_racine(project_id), config.session)
    if jeton is None:
        # Le message nomme la variable et le fichier, jamais une valeur.
        raise HTTPException(
            status_code=409,
            detail=(
                f"La variable `{config.session.jeton_env}` est absente ou vide "
                f"dans `{config.session.fichier_env}` du projet « {project_id} » : "
                "les captures ouvrent une session avec elle. Renseigne-la, puis "
                "recommence."
            ),
        )
    return jeton


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
    jeton = _jeton(project_id, config)
    if not await captures.app_repond(config.url):
        raise HTTPException(
            status_code=409,
            detail=(
                f"L'app du projet « {project_id} » ne répond pas à {config.url}. "
                "Lance-la d'abord, puis recommence."
            ),
        )
    try:
        noms = await captures.capturer(project_id, config, jeton=jeton)
    except captures.CapturesEchouees as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"captures": noms}


@router.get("/{project_id}/captures")
async def lister_les_captures_du_run(
    project_id: str, ticket: str = Query(...)
) -> dict[str, list[str]]:
    """List the images a run took for this ticket (ticket-620)."""
    _racine(project_id)
    if not captures.MOTIF_TICKET.fullmatch(ticket):
        raise HTTPException(status_code=404, detail="Capture inconnue")
    return {"captures": captures.lister_les_captures(project_id, ticket)}


@router.get("/{project_id}/captures/{fichier}")
async def servir_une_capture(
    project_id: str, fichier: str, ticket: str | None = Query(default=None)
) -> FileResponse:
    _racine(project_id)
    if ticket is not None and not captures.MOTIF_TICKET.fullmatch(ticket):
        raise HTTPException(status_code=404, detail="Capture inconnue")
    # Le motif seul exclut `..`, `/` et `\` : pas de traversée de chemin.
    chemin = captures.dossier_des_captures(project_id, ticket) / fichier
    if not captures.MOTIF_FICHIER.fullmatch(fichier) or not chemin.is_file():
        raise HTTPException(status_code=404, detail="Capture inconnue")
    return FileResponse(chemin, media_type="image/png")
