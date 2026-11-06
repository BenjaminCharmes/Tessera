"""Supervision recap: what the supervisor did and what it left to the user (ticket-860, ADR-080).

Read-only. The journal `memory/supervision.md` is written by the service alone
(ADR-080); this route only reads it, so it grants no power and needs no `Origin`.
"""
from datetime import date

from fastapi import APIRouter
from pydantic import BaseModel

from tessera.config import settings
from tessera.services.supervision.superviseur_journal import LigneJournal, cas_a_toi_ouverts, lire_journal

#: The project whose backlog and journal the supervisor keeps: Tessera itself.
PROJET_SUPERVISE = "ide-core"
#: A recap is a summary: the most recent lines only.
LIGNES_MAX = 200

router = APIRouter(tags=["supervision"])


class LigneRecap(BaseModel):
    """One journal line, as the UI shows it."""

    jour: date
    action: str
    cible: str
    sha: str
    resume: str


class CasAToi(BaseModel):
    """An open « À toi » case, with the supervisor's recommendation."""

    jour: date
    cible: str
    recommandation: str


class RecapSupervision(BaseModel):
    """Body of ``GET /supervision/recap``."""

    depuis: date | None
    lignes: list[LigneRecap]
    a_toi: list[CasAToi]


def _plus_recentes_d_abord(lignes: list[LigneJournal]) -> list[LigneJournal]:
    """Newest day first; within a day, the later line of the file first."""
    return sorted(reversed(lignes), key=lambda ligne: ligne.jour, reverse=True)


@router.get("/supervision/recap", response_model=RecapSupervision)
async def get_supervision_recap(depuis: date | None = None) -> RecapSupervision:
    """The journal since ``depuis`` (newest first, 200 lines at most) and the open cases.

    An unreadable ``depuis`` is a 422 (FastAPI validation). A date in the future gives
    no line. The open cases do not depend on ``depuis``: a case stays open until a
    `resolu` line closes it, whatever its age.
    """
    memoire = settings.ide_workspace_dir / PROJET_SUPERVISE / "memory"
    journal = lire_journal(memoire)
    lignes = [ligne for ligne in journal if depuis is None or ligne.jour >= depuis]
    return RecapSupervision(
        depuis=depuis,
        lignes=[
            LigneRecap(
                jour=ligne.jour, action=ligne.action, cible=ligne.cible,
                sha=ligne.sha, resume=ligne.resume,
            )
            for ligne in _plus_recentes_d_abord(lignes)[:LIGNES_MAX]
        ],
        a_toi=[
            CasAToi(jour=cas.jour, cible=cas.cible, recommandation=cas.resume)
            for cas in _plus_recentes_d_abord(cas_a_toi_ouverts(journal))
        ],
    )
