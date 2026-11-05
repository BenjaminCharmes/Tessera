"""Read and change the five global settings (ADR-075, ticket-808).

Une écriture exige un `Origin` déclaré : le contrôle est dans `auth.py`, avant
d'arriver ici. Un nom hors registre est un 404 qui ne le nomme pas.
"""
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from tessera import reglages
from tessera.config import settings
from tessera.services.run_registry import RUN_REGISTRY

router = APIRouter(prefix="/reglages", tags=["reglages"])


class ValeurAEcrire(BaseModel):
    """Body of a PUT: the raw value, validated by the registry."""

    valeur: Any


def _runs_ouverts(nom: str) -> int:
    """Open runs still holding an older value of a per-run setting."""
    if reglages.REGISTRE[nom].effet != "prochain_run":
        return 0
    actuelle = getattr(reglages.du_moment(), nom)
    return sum(1 for run in RUN_REGISTRY.vivants() if getattr(run.reglages, nom) != actuelle)


def _element(nom: str) -> dict[str, Any]:
    reglage = reglages.REGISTRE[nom]
    return {
        "nom": nom,
        "libelle": reglage.libelle,
        "type": reglage.type,
        "valeur": getattr(reglages.du_moment(), nom),
        "defaut": getattr(settings, nom),
        "minimum": reglage.minimum,
        "maximum": reglage.maximum,
        "modifie": nom in reglages.noms_modifies(),
        "effet": reglage.effet,
        "runs_ouverts": _runs_ouverts(nom),
    }


def _connu(nom: str) -> str:
    """Return the name if it is in the registry, else a 404 that does not echo it."""
    if nom not in reglages.REGISTRE:
        raise HTTPException(status_code=404, detail="Réglage introuvable")
    return nom


@router.get("")
async def lister() -> list[dict[str, Any]]:
    """The five settings: value of the next run, `.env` default, bounds, effect."""
    return [_element(nom) for nom in reglages.REGISTRE]


@router.put("/{nom}")
async def poser(nom: str, corps: ValeurAEcrire) -> dict[str, Any]:
    """Override a setting; 422 when out of bounds or of the wrong type."""
    _connu(nom)
    try:
        await reglages.ecrire(settings.ide_db_path, nom, corps.valeur)
    except reglages.ReglageInvalide as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _element(nom)


@router.delete("/{nom}")
async def rendre(nom: str) -> dict[str, Any]:
    """Drop the override: the setting returns to its `.env` default."""
    await reglages.retirer(settings.ide_db_path, _connu(nom))
    return _element(nom)
