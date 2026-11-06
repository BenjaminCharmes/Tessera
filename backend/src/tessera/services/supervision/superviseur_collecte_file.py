"""The interrupted queues a restart can be offered for — ticket-867, ADR-080.

A candidate `relancer_file` exists when the project declared `relance_file`
(ticket-852) and its newest run is a queue that stopped on an infrastructure
cut. The idempotence `sha` is the cause: one restart per queue and per cause. A
queue stopped on a verdict (« non approuvé »), a missing ticket, money or a
requested stop offers nothing — `classer_interruption` reads the cause, and
fails closed. The action calls no model.

The queue comes from the usage base: its envelope row carries the stop line
(`arret`), and its last `queue_progress` event carries the tickets it still
held. A later run of the project, of any kind, makes the queue stale: someone
has already taken the project back. Tickets the queue approved, or that are done
or cancelled, are never restarted. A queue that never reported progress has no
known tickets and offers nothing.
"""
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

import aiosqlite

from tessera.models.superviseur_config import ConfigSuperviseur
from tessera.services.noyau.pipeline_events import EventType
from tessera.services.supervision.anomalies.lecture_base import ouvrir_en_lecture
from tessera.services.supervision.superviseur_actions import Action, Decision
from tessera.services.supervision.superviseur_boucle_ports import Candidat
from tessera.services.supervision.superviseur_file import FileCoupee, SuperviseurFile, classer_interruption, tickets_restants

_MARQUE = "file interrompue"


@dataclass(frozen=True)
class SourcesFile:
    """What the collector reads: the interrupted queues of the project."""

    files: Callable[[], Awaitable[list[FileCoupee]]]


async def _derniere_file_coupee(db: aiosqlite.Connection, project_id: str) -> tuple[str, str] | None:
    """`(run id, stop line)` of the project's newest run when it is an interrupted queue."""
    requete = (
        "SELECT id, mode, final_status, arret FROM pipeline_runs"
        " WHERE project_id = ? AND parent_run_id IS NULL ORDER BY started_at DESC, rowid DESC LIMIT 1"
    )
    async with db.execute(requete, (project_id,)) as curseur:
        ligne = await curseur.fetchone()
    if ligne is None:
        return None
    run_id, mode, statut, arret = ligne
    if mode != "queue" or statut != "interrupted" or not isinstance(arret, str) or _MARQUE not in arret:
        return None
    return str(run_id), arret


async def _approuves(db: aiosqlite.Connection, run_id: str) -> set[str]:
    async with db.execute("SELECT ticket_id FROM pipeline_runs WHERE parent_run_id = ? AND approved = 1", (run_id,)) as curseur:
        return {str(ligne[0]) for ligne in await curseur.fetchall()}


async def _tickets_de_la_file(db: aiosqlite.Connection, run_id: str) -> list[str]:
    """The current ticket then the ones after it, from the queue's last progress event."""
    requete = "SELECT ticket_id, data_json FROM agent_events WHERE run_id = ? AND type = ? ORDER BY id DESC LIMIT 1"
    async with db.execute(requete, (run_id, EventType.QUEUE_PROGRESS.value)) as curseur:
        ligne = await curseur.fetchone()
    if ligne is None or not isinstance(ligne[1], str):
        return []
    try:
        donnees = json.loads(ligne[1])
    except ValueError:
        return []
    suite = donnees.get("restants") if isinstance(donnees, dict) else None
    courant = [str(ligne[0])] if ligne[0] else []
    return courant + [t for t in suite if isinstance(t, str)] if isinstance(suite, list) else courant


async def files_coupees(db_path: Path | str, project_id: str, finis: Callable[[], Awaitable[set[str]]]) -> list[FileCoupee]:
    """The interrupted queue of `project_id` with what it still held, or none."""
    async with ouvrir_en_lecture(db_path) as db:
        coupee = await _derniere_file_coupee(db, project_id)
        if coupee is None:
            return []
        run_id, ligne = coupee
        prevus = await _tickets_de_la_file(db, run_id)
        termines = await _approuves(db, run_id)
    restants = tickets_restants(list(dict.fromkeys(prevus)), sorted(termines | await finis()))
    return [FileCoupee(project_id, run_id, ligne, restants)] if restants else []


def _relancer(superviseur: Callable[[], SuperviseurFile], coupee: FileCoupee) -> Callable[[], Awaitable[list[Decision]]]:
    """The execution of one restart, with its queue bound to it."""

    async def executer() -> list[Decision]:
        return [await superviseur().relancer(coupee)]

    return executer


async def candidats_file(
    project_id: str, config: ConfigSuperviseur, sources: SourcesFile, superviseur: Callable[[], SuperviseurFile]
) -> list[Candidat]:
    """One `relancer_file` candidate per queue cut by the infrastructure, when `relance_file` is declared."""
    if not config.relance_file:
        return []
    candidats: list[Candidat] = []
    for coupee in await sources.files():
        cause = classer_interruption(coupee.ligne)
        if cause != "infrastructure":
            continue
        cible = f"{project_id} file {coupee.run_id}"
        candidats.append(Candidat(project_id, Action.RELANCER_FILE, cible, cause, True, _relancer(superviseur, coupee)))
    return candidats
