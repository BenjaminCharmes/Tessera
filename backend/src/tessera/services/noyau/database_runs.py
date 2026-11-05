from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite
from pydantic import BaseModel


class PipelineRunSummary(BaseModel):
    id: str
    ticket_id: str
    started_at: str
    finished_at: str | None = None
    rounds: int | None = None
    approved: bool | None = None
    final_status: str | None = None
    total_cost_usd: float = 0.0
    arret: str | None = None
    parent_run_id: str | None = None


async def create_run(
    db_path: Path | str,
    project_id: str,
    ticket_id: str,
    mode: str = "single",
    parent_run_id: str | None = None,
    run_id: str | None = None,
) -> str:
    """Insert a new pipeline run row and return its id.

    `mode` is one of ``single`` (default), ``queue`` or ``autonomous``.  Queue
    and autonomous rows are envelope runs that carry pipeline events but hold no
    agent calls; statistics queries exclude them so they do not inflate run
    counts or quality metrics.

    `parent_run_id` links a per-ticket run (created inside a queue or autonomous
    run) to its envelope row. Events are stored on the envelope; this link lets
    the events endpoint filter them by ticket.

    `run_id` lets the caller choose the row id (ticket-431): the launch id that
    ``POST /orchestrator/run`` hands back becomes the row's id, so the run can be
    followed with it. Default: a fresh uuid.
    """
    run_id = run_id or str(uuid.uuid4())
    started_at = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(str(db_path)) as db:
        await db.execute(
            "INSERT INTO pipeline_runs (id, project_id, ticket_id, started_at, mode, parent_run_id)"
            " VALUES (?,?,?,?,?,?)",
            (run_id, project_id, ticket_id, started_at, mode, parent_run_id),
        )
        await db.commit()
    return run_id


async def finish_run(
    db_path: Path | str,
    run_id: str,
    rounds: int,
    approved: bool,
    final_status: str,
    arret: str | None = None,
) -> None:
    finished_at = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(str(db_path)) as db:
        await db.execute(
            """UPDATE pipeline_runs
               SET finished_at=?, rounds=?, approved=?, final_status=?, arret=?
               WHERE id=?""",
            (finished_at, rounds, int(approved), final_status, arret, run_id),
        )
        await db.commit()


#: La cause écrite sur un run que le processus a laissé derrière lui.
CAUSE_RUN_ORPHELIN = "backend restarted: the run's process is gone"


async def solder_les_runs_orphelins(db_path: Path | str) -> list[str]:
    """Settles every run left without `finished_at` — ticket-177.

    Un backend local n'a qu'un processus (ADR-038) : au démarrage, un run
    encore « en cours » en base est celui d'un processus qui n'est plus là.
    Un `kill` n'exécute aucun `finally`, donc ni ADR-037 ni le commit de fin
    de run n'ont eu lieu. On solde en `blocked`, jamais en approuvé, en
    laissant intacts les événements et les coûts déjà enregistrés, et on
    écrit la cause comme un événement `error`, pour que l'historique la
    montre. Le jour où deux backends partageraient une base, cette hypothèse
    tomberait : elle est ici, pas supposée ailleurs.
    """
    maintenant = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(str(db_path)) as db:
        async with db.execute(
            "SELECT id, rounds FROM pipeline_runs WHERE finished_at IS NULL"
        ) as cursor:
            orphelins = await cursor.fetchall()
        for run_id, rounds in orphelins:
            await db.execute(
                "INSERT INTO agent_events (run_id, type, agent, data_json, ts) VALUES (?,?,?,?,?)",
                (
                    run_id, "error", None,
                    json.dumps({"reason": "interrupted", "detail": CAUSE_RUN_ORPHELIN}),
                    maintenant,
                ),
            )
            await db.execute(
                """UPDATE pipeline_runs
                   SET finished_at=?, rounds=?, approved=0, final_status='blocked',
                       arret=?
                   WHERE id=?""",
                (maintenant, int(rounds or 0), CAUSE_RUN_ORPHELIN, run_id),
            )
        await db.commit()
    return [str(run_id) for run_id, _ in orphelins]


async def list_runs(
    db_path: Path | str,
    project_id: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    async with aiosqlite.connect(str(db_path)) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT pr.id, pr.ticket_id, pr.started_at, pr.finished_at,
                      pr.rounds, pr.approved, pr.final_status, pr.arret,
                      pr.parent_run_id,
                      COALESCE(SUM(ac.cost_usd), 0.0) as total_cost_usd
               FROM pipeline_runs pr
               LEFT JOIN agent_calls ac ON ac.run_id = pr.id
               WHERE pr.project_id=?
               GROUP BY pr.id
               -- `rowid` départage à égalité d'horodatage. Deux runs créés
               -- dans la même milliseconde laissaient SQLite trancher seul :
               -- l'historique s'affichait alors dans un ordre variable, et le
               -- test d'ordre échouait une fois sur quelques dizaines.
               ORDER BY pr.started_at DESC, pr.rowid DESC
               LIMIT ?""",
            (project_id, limit),
        ) as cursor:
            rows = await cursor.fetchall()
    return [
        {
            "id": row["id"],
            "ticket_id": row["ticket_id"],
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "rounds": row["rounds"],
            "approved": bool(row["approved"]) if row["approved"] is not None else None,
            "final_status": row["final_status"],
            "arret": row["arret"],
            "parent_run_id": row["parent_run_id"],
            "total_cost_usd": float(row["total_cost_usd"]),
        }
        for row in rows
    ]


async def list_runs_for_ticket(
    db_path: Path | str,
    project_id: str,
    ticket_id: str,
) -> list[dict[str, Any]]:
    """Return runs for one ticket, newest first — ticket-327.

    Filters by both `project_id` and `ticket_id` in SQL so the caller never
    receives rows from another project. Uses the covering index added in
    migration #6 to avoid a full-table scan.

    Queue and autonomous envelopes are left out (ticket-333): they carry the
    first ticket's id but replay the whole queue, as `usage_stats` already
    assumes (ticket-263).
    """
    async with aiosqlite.connect(str(db_path)) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT pr.id, pr.started_at, pr.finished_at,
                      pr.rounds, pr.approved, pr.final_status, pr.arret,
                      COALESCE(SUM(ac.cost_usd), 0.0) AS total_cost_usd
               FROM pipeline_runs pr
               LEFT JOIN agent_calls ac ON ac.run_id = pr.id
               WHERE pr.project_id = ? AND pr.ticket_id = ?
                 AND (pr.mode IS NULL OR pr.mode = 'single')
               GROUP BY pr.id
               ORDER BY pr.started_at DESC, pr.rowid DESC""",
            (project_id, ticket_id),
        ) as cursor:
            rows = await cursor.fetchall()
    return [
        {
            "id": row["id"],
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "rounds": row["rounds"],
            "approved": bool(row["approved"]) if row["approved"] is not None else None,
            "final_status": row["final_status"],
            "arret": row["arret"],
            "total_cost_usd": float(row["total_cost_usd"]),
        }
        for row in rows
    ]
