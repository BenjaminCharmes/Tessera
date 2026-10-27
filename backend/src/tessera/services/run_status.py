"""Where a run stands, live or finished — ticket-431.

A live run is read from the registry. A finished one is read from the
database: the envelope row, its per-ticket children, and the last
``queue_progress`` event stored under it.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite
from pydantic import BaseModel, computed_field

from tessera.services.run_registry import RunActif

EN_COURS = "en cours"
TERMINE = "terminé"
INTERROMPU = "interrompu"

#: `final_status` d'un run qui n'est pas allé au bout : l'exception qui a coupé
#: le run (`interrupted`) ou le ticket arrêté sur un blocage (`blocked`).
_FINAUX_INTERROMPUS = frozenset({"interrupted", "blocked"})


#: Longueur maximale du motif rendu : la cause complète vit dans l'historique.
_MOTIF_MAX = 200


class TicketArrete(BaseModel):
    """A ticket the queue played that did not end approved — ticket-444."""

    ticket_id: str
    motif: str | None = None


class RunStatus(BaseModel):
    """What ``GET /runs/{run_id}`` answers.

    ``approuves`` ended approved; ``arretes`` stopped (blocked, unapproved,
    interrupted); ``restants`` have not produced a result and can be launched
    again. ``faits`` is deprecated: always ``approuves`` followed by the
    tickets of ``arretes``.
    """

    project_id: str
    mode: str
    statut: str
    ticket_courant: str | None = None
    approuves: list[str]
    arretes: list[TicketArrete]
    restants: list[str]
    debut: str
    fin: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def faits(self) -> list[str]:
        """Deprecated: ``approuves`` + the tickets of ``arretes``."""
        return [*self.approuves, *(a.ticket_id for a in self.arretes)]


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
        # Une file s'arrête au premier ticket non approuvé : tant qu'elle
        # tourne, ce qu'elle a laissé derrière elle est approuvé.
        approuves=list(run.file_faits),
        arretes=[],
        restants=run.restants(),
        debut=en_utc(run.demarre_a),
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


def _motif_court(arret: str | None) -> str | None:
    """First line of the stop cause, cut to a readable length."""
    if not arret or not arret.strip():
        return None
    ligne = arret.strip().splitlines()[0]
    return ligne if len(ligne) <= _MOTIF_MAX else ligne[: _MOTIF_MAX - 1] + "…"


class _Classement(BaseModel):
    """The envelope's children sorted by how they ended."""

    approuves: list[str] = []
    arretes: list[TicketArrete] = []
    coupes: list[str] = []
    en_cours: str | None = None


def classer_les_tickets(lignes: list[aiosqlite.Row], file_finie: bool) -> _Classement:
    """Sort child rows: approved, stopped, or cut before any result (`todo`).

    A row without an end under a finished queue is stopped, never approved;
    under a queue still open it is the current ticket.
    """
    # Un ticket resté `todo` sans approbation (limite de session, plafond par
    # ticket) n'est pas arrêté : il se relance tel quel, donc il reste à faire.
    c = _Classement()
    for ligne in lignes:
        ticket = str(ligne["ticket_id"])
        if ligne["finished_at"] is None and not file_finie:
            c.en_cours = ticket
        elif ligne["finished_at"] is None:
            c.arretes.append(TicketArrete(ticket_id=ticket, motif="no outcome recorded"))
        elif ligne["approved"]:
            c.approuves.append(ticket)
        elif ligne["final_status"] == "todo":
            c.coupes.append(ticket)
        else:
            c.arretes.append(TicketArrete(ticket_id=ticket, motif=_motif_court(ligne["arret"])))
    return c


async def _tickets_joues(db: aiosqlite.Connection, run_id: str) -> list[aiosqlite.Row]:
    """The envelope's children, in start order."""
    async with db.execute(
        "SELECT ticket_id, approved, final_status, arret, finished_at"
        " FROM pipeline_runs WHERE parent_run_id=? ORDER BY started_at, rowid",
        (run_id,),
    ) as cursor:
        return list(await cursor.fetchall())


def en_utc(instant: datetime | str) -> str:
    """ISO 8601 in UTC; a naive instant is taken as UTC, as the database stores it."""
    valeur = datetime.fromisoformat(instant) if isinstance(instant, str) else instant
    if valeur.tzinfo is None:
        valeur = valeur.replace(tzinfo=timezone.utc)
    return valeur.astimezone(timezone.utc).isoformat()


async def statut_en_base(db_path: Path | str, run_id: str) -> RunStatus | None:
    """Status of a run read from `pipeline_runs`; ``None`` if the id is unknown."""
    async with aiosqlite.connect(str(db_path)) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT project_id, mode, ticket_id, started_at, finished_at, final_status,"
            " approved, arret FROM pipeline_runs WHERE id=?",
            (run_id,),
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return None
        # Un run `single` n'a pas d'enfant : c'est sa propre ligne qui porte
        # l'issue de son ticket.
        lignes = [row] if (row["mode"] or "single") == "single" else await _tickets_joues(db, run_id)
        annonces = await _derniers_restants(db, run_id)

    fini = row["finished_at"] is not None
    classement = classer_les_tickets(lignes, fini)
    restants = [*classement.coupes, *(t for t in annonces if t not in classement.coupes)]
    return RunStatus(
        project_id=row["project_id"],
        mode=row["mode"] or "single",
        statut=statut_d_un_run_termine(row["final_status"], restants) if fini else EN_COURS,
        ticket_courant=classement.en_cours,
        approuves=classement.approuves,
        arretes=classement.arretes,
        restants=restants,
        debut=en_utc(row["started_at"]),
        fin=row["finished_at"],
    )
