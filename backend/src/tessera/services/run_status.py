"""Where a run stands, live or finished — ticket-431.

A live run is read from the registry. A finished one is read from the
database: the envelope row, its per-ticket children, and the last
``queue_progress`` event stored under it.
"""
import json
from pathlib import Path

import aiosqlite
from pydantic import BaseModel

from tessera.services.run_registry import RunActif

EN_COURS = "en cours"
TERMINE = "terminé"
INTERROMPU = "interrompu"

#: `final_status` d'un run qui n'est pas allé au bout : l'exception qui a coupé
#: le run (`interrupted`) ou le ticket arrêté sur un blocage (`blocked`).
_FINAUX_INTERROMPUS = frozenset({"interrupted", "blocked"})


class RunStatus(BaseModel):
    """What ``GET /runs/{run_id}`` answers."""

    project_id: str
    mode: str
    statut: str
    ticket_courant: str | None = None
    faits: list[str]
    restants: list[str]
    debut: str
    fin: str | None = None


def statut_d_un_run_termine(final_status: str | None, restants: list[str]) -> str:
    """`interrompu` when the run stopped early, `terminé` when it went through.

    Une file arrêtée sur budget, sur limite de session ou sur un ticket non
    approuvé laisse des `restants` : c'est ce qui la distingue d'une file allée
    au bout, car `final_status` ne décrit que le dernier ticket.
    """
    if restants or final_status in _FINAUX_INTERROMPUS:
        return INTERROMPU
    return TERMINE


def statut_d_un_run_vivant(run: RunActif) -> RunStatus:
    """The registry entry, in the shape of the status endpoint."""
    return RunStatus(
        project_id=run.project_id,
        mode=run.mode,
        statut=EN_COURS,
        ticket_courant=run.ticket_id,
        faits=list(run.file_faits),
        restants=list(run.file_restants),
        debut=run.demarre_a.isoformat(),
    )


async def _derniers_restants(db: aiosqlite.Connection, run_id: str) -> list[str]:
    """Remaining tickets announced by the last `queue_progress`, if any."""
    async with db.execute(
        "SELECT data_json FROM agent_events"
        " WHERE run_id=? AND type='queue_progress' ORDER BY id DESC LIMIT 1",
        (run_id,),
    ) as cursor:
        ligne = await cursor.fetchone()
    if ligne is None:
        return []
    restants = json.loads(ligne[0] or "{}").get("restants")
    if not isinstance(restants, list):
        return []
    return [str(t) for t in restants]


async def _tickets_faits(db: aiosqlite.Connection, run_id: str) -> list[str]:
    """Tickets the queue played: the envelope's children, in start order."""
    async with db.execute(
        "SELECT ticket_id FROM pipeline_runs WHERE parent_run_id=?"
        " ORDER BY started_at, rowid",
        (run_id,),
    ) as cursor:
        return [str(ligne[0]) for ligne in await cursor.fetchall()]


async def statut_en_base(db_path: Path | str, run_id: str) -> RunStatus | None:
    """Status of a run read from `pipeline_runs`; ``None`` if the id is unknown."""
    async with aiosqlite.connect(str(db_path)) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT project_id, mode, started_at, finished_at, final_status"
            " FROM pipeline_runs WHERE id=?",
            (run_id,),
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return None
        faits = await _tickets_faits(db, run_id)
        restants = await _derniers_restants(db, run_id)

    if row["finished_at"] is None:
        statut = EN_COURS
    else:
        statut = statut_d_un_run_termine(row["final_status"], restants)
    return RunStatus(
        project_id=row["project_id"],
        mode=row["mode"] or "single",
        statut=statut,
        faits=faits,
        restants=restants,
        debut=row["started_at"],
        fin=row["finished_at"],
    )
