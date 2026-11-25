"""Gaps in the backend's heartbeat — ticket-1046.

A beat every minute keeps the last instant in the local database. A gap longer
than `ECART_MIN` between two beats is an interruption: the PC was asleep or the
backend was stopped (the two cannot be told apart, and this says no more).
Instants are naive local `datetime.now()`, like the rituals' `derniere`.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path

import aiosqlite
from pydantic import BaseModel

from tessera.config import settings

_logger = logging.getLogger(__name__)

PERIODE_S = 60
ECART_MIN = timedelta(minutes=10)
GARDEES = 30


class Interruption(BaseModel):
    debut: datetime
    fin: datetime


class ListeInterruptions(BaseModel):
    interruptions: list[Interruption]


async def battre(db_path: Path | str, maintenant: datetime) -> Interruption | None:
    """Record a beat; return the interruption it reveals, if any."""
    async with aiosqlite.connect(str(db_path)) as db:
        curseur = await db.execute("SELECT dernier FROM veille_battement WHERE id = 1")
        ligne = await curseur.fetchone()
        precedent = datetime.fromisoformat(ligne[0]) if ligne else None
        interruption: Interruption | None = None
        if precedent is not None and maintenant - precedent > ECART_MIN:
            interruption = Interruption(debut=precedent, fin=maintenant)
            await db.execute(
                "INSERT INTO veille_interruptions (debut, fin) VALUES (?, ?)",
                (precedent.isoformat(), maintenant.isoformat()),
            )
            await db.execute(
                "DELETE FROM veille_interruptions WHERE id NOT IN "
                "(SELECT id FROM veille_interruptions ORDER BY id DESC LIMIT ?)",
                (GARDEES,),
            )
        await db.execute(
            "INSERT INTO veille_battement (id, dernier) VALUES (1, ?) "
            "ON CONFLICT(id) DO UPDATE SET dernier = excluded.dernier",
            (maintenant.isoformat(),),
        )
        await db.commit()
    return interruption


async def lister(db_path: Path | str) -> ListeInterruptions:
    """The kept interruptions, most recent first."""
    async with aiosqlite.connect(str(db_path)) as db:
        curseur = await db.execute("SELECT debut, fin FROM veille_interruptions ORDER BY id DESC")
        lignes = await curseur.fetchall()
    return ListeInterruptions(
        interruptions=[
            Interruption(debut=datetime.fromisoformat(d), fin=datetime.fromisoformat(f))
            for d, f in lignes
        ]
    )


async def battre_sans_lever(db_path: Path | str) -> None:
    """One beat at the PC's local time; a failed write is logged, never raised."""
    try:
        await battre(db_path, datetime.now())
    except Exception:  # noqa: BLE001 — le battement est un témoin, pas une condition
        _logger.exception("veille_battement_echec")


async def boucle() -> None:
    """Beat every `PERIODE_S` until cancelled."""
    while True:
        await battre_sans_lever(settings.ide_db_path)
        await asyncio.sleep(PERIODE_S)


def demarrer() -> "asyncio.Task[None]":
    """Start the beat in the running loop."""
    return asyncio.create_task(boucle())


async def arreter(tache: "asyncio.Task[None]") -> None:
    """Stop the beat and wait for it."""
    tache.cancel()
    try:
        await tache
    except asyncio.CancelledError:
        pass
