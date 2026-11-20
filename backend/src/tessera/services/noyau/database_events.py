from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import aiosqlite


async def save_event(
    db_path: Path | str,
    run_id: str,
    event_type: str,
    agent: str | None,
    data: dict[str, Any],
    timestamp: str,
    ticket_id: str | None = None,
) -> None:
    async with aiosqlite.connect(str(db_path)) as db:
        await db.execute(
            "INSERT INTO agent_events (run_id, type, agent, data_json, ts, ticket_id)"
            " VALUES (?,?,?,?,?,?)",
            (run_id, event_type, agent, json.dumps(data), timestamp, ticket_id or None),
        )
        await db.commit()


async def get_run_events(
    db_path: Path | str,
    run_id: str,
) -> list[dict[str, Any]] | None:
    """Return persisted events for a run, excluding agent_token streaming chunks.

    Returns ``None`` when the run_id is unknown (caller maps this to 404).

    For a per-ticket row inside a queue (``parent_run_id`` set), events are
    fetched from the parent run and filtered by the row's ``ticket_id``,
    because ``emetteur`` stores all events under the envelope. For a standalone
    run or a queue envelope, all non-token events are returned.

    The filter is applied in SQL to avoid loading large token streams into
    memory (see ticket-280 risk section).
    """
    async with aiosqlite.connect(str(db_path)) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, ticket_id, parent_run_id FROM pipeline_runs WHERE id=?",
            (run_id,),
        ) as cursor:
            row = await cursor.fetchone()

        if row is None:
            return None

        parent_run_id: str | None = row["parent_run_id"]
        ticket_id: str | None = row["ticket_id"]

        if parent_run_id is not None and ticket_id:
            # Per-ticket queue row: events live on the parent, filtered by ticket.
            async with db.execute(
                """SELECT type, agent, data_json, ts
                   FROM agent_events
                   WHERE run_id=? AND ticket_id=? AND type != 'agent_token'
                   ORDER BY ts, id""",
                (parent_run_id, ticket_id),
            ) as cursor:
                event_rows = await cursor.fetchall()
        else:
            # Standalone run or queue envelope: return all non-token events.
            async with db.execute(
                """SELECT type, agent, data_json, ts
                   FROM agent_events
                   WHERE run_id=? AND type != 'agent_token'
                   ORDER BY ts, id""",
                (run_id,),
            ) as cursor:
                event_rows = await cursor.fetchall()

    return [
        {
            "type": r["type"],
            "agent": r["agent"],
            "data": json.loads(r["data_json"] or "{}"),
            "timestamp": r["ts"],
        }
        for r in event_rows
    ]
