"""Rituals routes — ticket-902."""
from datetime import datetime

from fastapi import APIRouter, HTTPException

from tessera.config import settings
from tessera.services.projets import rituels as service

router = APIRouter(prefix="/rituels", tags=["rituels"])


def _verifier(identifiant: str) -> None:
    definitions, _ = service.lire_definitions()
    if identifiant not in {d.id for d in definitions}:
        raise HTTPException(status_code=404, detail="Unknown ritual")


@router.get("", response_model=service.ListeRituels)
async def get_rituels() -> service.ListeRituels:
    """Rituals of `rituels.md` with their status at the PC's local time."""
    return await service.lister(settings.ide_db_path, datetime.now())


@router.post("/{identifiant}/fait", status_code=204)
async def post_fait(identifiant: str) -> None:
    """Mark a ritual done now."""
    _verifier(identifiant)
    await service.marquer_fait(settings.ide_db_path, identifiant, datetime.now())


@router.post("/{identifiant}/reporter", status_code=204)
async def post_reporter(identifiant: str) -> None:
    """Postpone a ritual by 24 hours."""
    _verifier(identifiant)
    await service.reporter(settings.ide_db_path, identifiant, datetime.now())
