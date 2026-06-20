from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite
from pydantic import BaseModel

_CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id           TEXT PRIMARY KEY,
    project_id   TEXT NOT NULL,
    ticket_id    TEXT NOT NULL,
    started_at   TEXT NOT NULL,
    finished_at  TEXT,
    rounds       INTEGER,
    approved     INTEGER,
    final_status TEXT
);

CREATE TABLE IF NOT EXISTS agent_events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id     TEXT NOT NULL REFERENCES pipeline_runs(id),
    type       TEXT NOT NULL,
    agent      TEXT,
    data_json  TEXT,
    ts         TEXT NOT NULL
);
"""


class PipelineRunSummary(BaseModel):
    id: str
    ticket_id: str
    started_at: str
    finished_at: str | None = None
    rounds: int | None = None
    approved: bool | None = None
    final_status: str | None = None


async def init_db(db_path: Path | str) -> None:
    async with aiosqlite.connect(str(db_path)) as db:
        await db.executescript(_CREATE_TABLES)
        await db.execute("PRAGMA journal_mode=WAL")
        await db.commit()


async def create_run(db_path: Path | str, project_id: str, ticket_id: str) -> str:
    run_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(str(db_path)) as db:
        await db.execute(
            "INSERT INTO pipeline_runs (id, project_id, ticket_id, started_at) VALUES (?,?,?,?)",
            (run_id, project_id, ticket_id, started_at),
        )
        await db.commit()
    return run_id


async def finish_run(
    db_path: Path | str,
    run_id: str,
    rounds: int,
    approved: bool,
    final_status: str,
) -> None:
    finished_at = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(str(db_path)) as db:
        await db.execute(
            """UPDATE pipeline_runs
               SET finished_at=?, rounds=?, approved=?, final_status=?
               WHERE id=?""",
            (finished_at, rounds, int(approved), final_status, run_id),
        )
        await db.commit()


async def save_event(
    db_path: Path | str,
    run_id: str,
    event_type: str,
    agent: str | None,
    data: dict[str, Any],
    timestamp: str,
) -> None:
    async with aiosqlite.connect(str(db_path)) as db:
        await db.execute(
            "INSERT INTO agent_events (run_id, type, agent, data_json, ts) VALUES (?,?,?,?,?)",
            (run_id, event_type, agent, json.dumps(data), timestamp),
        )
        await db.commit()


async def list_runs(
    db_path: Path | str,
    project_id: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    async with aiosqlite.connect(str(db_path)) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT id, ticket_id, started_at, finished_at, rounds, approved, final_status
               FROM pipeline_runs
               WHERE project_id=?
               ORDER BY started_at DESC
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
        }
        for row in rows
    ]
