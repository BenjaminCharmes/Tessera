"""Recurring rituals read from `rituels.md` at the repository root — ticket-902.

The list follows the repository; the done/postponed state stays in the local
database (`rituels_etat`) and never leaves the PC.
"""
import logging
from datetime import datetime, timedelta
from pathlib import Path

import aiosqlite
import frontmatter
from pydantic import BaseModel, ValidationError

from tessera.config import _REPO_ROOT
from tessera.services.projets.rituels_echeances import Echeances, Rythme, calculer_echeances

_logger = logging.getLogger(__name__)

FICHIER = _REPO_ROOT / "rituels.md"
REPORT = timedelta(hours=24)


class RituelDefini(BaseModel):
    id: str
    titre: str
    rythme: Rythme
    duree_min: int
    phrase: str
    detail: str
    projets: list[str] = []


class RituelVu(RituelDefini, Echeances):
    fait_le: datetime | None
    reporte_jusqua: datetime | None


class ListeRituels(BaseModel):
    rituels: list[RituelVu]
    erreur: str | None = None


def lire_definitions(chemin: Path | None = None) -> tuple[list[RituelDefini], str | None]:
    """Parse the file: (entries, None), or ([], message) when it is invalid."""
    chemin = chemin or FICHIER
    if not chemin.is_file():
        return [], None
    try:
        brut = frontmatter.loads(chemin.read_text(encoding="utf-8")).metadata.get("rituels", [])
        if not isinstance(brut, list):
            return [], "rituels: a list is expected"
        return [RituelDefini.model_validate(entree) for entree in brut], None
    except (ValidationError, ValueError, OSError) as exc:
        _logger.warning("rituels_illisibles", extra={"erreur": str(exc)})
        return [], f"rituels.md is invalid: {exc}"


async def _etats(db_path: Path | str) -> dict[str, tuple[datetime | None, datetime | None]]:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT id, fait_le, reporte_jusqua FROM rituels_etat") as cur:
            lignes = await cur.fetchall()
    return {
        str(i): (
            datetime.fromisoformat(f) if f else None,
            datetime.fromisoformat(r) if r else None,
        )
        for i, f, r in lignes
    }


def _ordre(rituel: RituelVu) -> tuple[int, datetime]:
    if rituel.statut == "en_retard" and rituel.derniere is not None:
        return 0, rituel.derniere
    return 1, rituel.prochaine or datetime.max


async def lister(
    db_path: Path | str, maintenant: datetime, chemin: Path | None = None
) -> ListeRituels:
    """Every ritual with its status, late ones first."""
    definitions, erreur = lire_definitions(chemin)
    etats = await _etats(db_path)
    vus: list[RituelVu] = []
    for d in definitions:
        fait_le, reporte = etats.get(d.id, (None, None))
        ech = calculer_echeances(d.rythme, maintenant, fait_le, reporte)
        vus.append(
            RituelVu(**d.model_dump(), **ech.model_dump(), fait_le=fait_le, reporte_jusqua=reporte)
        )
    return ListeRituels(rituels=sorted(vus, key=_ordre), erreur=erreur)


async def _ecrire(
    db_path: Path | str, identifiant: str, fait_le: datetime | None, reporte: datetime | None
) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT INTO rituels_etat (id, fait_le, reporte_jusqua) VALUES (?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET fait_le = COALESCE(excluded.fait_le, fait_le), "
            "reporte_jusqua = excluded.reporte_jusqua",
            (
                identifiant,
                fait_le.isoformat() if fait_le else None,
                reporte.isoformat() if reporte else None,
            ),
        )
        await db.commit()


async def marquer_fait(db_path: Path | str, identifiant: str, maintenant: datetime) -> None:
    """Set `fait_le` to now and clear the postponement."""
    await _ecrire(db_path, identifiant, maintenant, None)


async def reporter(db_path: Path | str, identifiant: str, maintenant: datetime) -> None:
    """Postpone by 24 hours, keeping any earlier `fait_le`."""
    await _ecrire(db_path, identifiant, None, maintenant + REPORT)
