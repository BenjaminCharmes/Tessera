"""Helpers shared by the anomaly detector tests: a real database, filled by hand."""
import json
from pathlib import Path
from typing import Any

import aiosqlite

from tessera.services.database import init_db


async def base_neuve(chemin: Path) -> Path:
    """Create an initialised database file and return its path."""
    await init_db(chemin)
    return chemin


async def ligne_de_run(
    db: Path,
    run_id: str,
    *,
    project_id: str = "p",
    ticket_id: str = "ticket-001",
    mode: str = "single",
    parent: str | None = None,
    started_at: str = "2026-11-05T10:00:00+00:00",
    finished_at: str | None = None,
    final_status: str | None = None,
    arret: str | None = None,
) -> None:
    async with aiosqlite.connect(str(db)) as c:
        await c.execute(
            "INSERT INTO pipeline_runs (id, project_id, ticket_id, started_at, finished_at,"
            " final_status, arret, mode, parent_run_id) VALUES (?,?,?,?,?,?,?,?,?)",
            (run_id, project_id, ticket_id, started_at, finished_at, final_status, arret,
             mode, parent),
        )
        await c.commit()


async def evenement(
    db: Path,
    run_id: str,
    type_: str,
    *,
    ts: str,
    ticket_id: str | None = "ticket-001",
    agent: str | None = None,
    data: dict[str, Any] | None = None,
) -> int:
    """Insert one event and return its row id."""
    async with aiosqlite.connect(str(db)) as c:
        curseur = await c.execute(
            "INSERT INTO agent_events (run_id, type, agent, data_json, ts, ticket_id)"
            " VALUES (?,?,?,?,?,?)",
            (run_id, type_, agent, json.dumps(data or {}), ts, ticket_id),
        )
        await c.commit()
        return int(curseur.lastrowid or 0)


async def appel_d_agent(
    db: Path, run_id: str, cout: float, *, ticket_id: str = "ticket-001"
) -> None:
    async with aiosqlite.connect(str(db)) as c:
        await c.execute(
            "INSERT INTO agent_calls (run_id, ticket_id, role, model, cost_usd, created_at)"
            " VALUES (?,?,?,?,?,?)",
            (run_id, ticket_id, "codeur", "m", cout, "2026-11-05T10:05:00+00:00"),
        )
        await c.commit()
