"""Database side of the startup repository recovery — ticket-665.

A run written `interrupted` (clean stop) is recovered once: `depot_repris_at`
records that its repository was put back in order.
"""

from __future__ import annotations

from datetime import datetime, timezone

import aiosqlite


async def runs_interrompus_a_reprendre(db: aiosqlite.Connection) -> list[str]:
    """Ids of `interrupted` runs whose repository was not recovered yet."""
    async with db.execute(
        "SELECT id FROM pipeline_runs"
        " WHERE final_status = 'interrupted' AND depot_repris_at IS NULL"
        " ORDER BY started_at"
    ) as cursor:
        return [str(row[0]) for row in await cursor.fetchall()]


async def lire_runs(
    db: aiosqlite.Connection, run_ids: list[str]
) -> list[tuple[str, str, str]]:
    """Reads `(project_id, ticket_id, started_at)` of the given runs, oldest first."""
    if not run_ids:
        return []
    placeholders = ",".join("?" * len(run_ids))
    async with db.execute(
        f"SELECT project_id, ticket_id, started_at"
        f" FROM pipeline_runs WHERE id IN ({placeholders}) ORDER BY started_at",
        run_ids,
    ) as cursor:
        return [(str(p), str(t), str(s)) for p, t, s in await cursor.fetchall()]


async def marquer_depots_repris(db: aiosqlite.Connection, run_ids: list[str]) -> None:
    """Marks the runs as recovered, so a later restart leaves them alone."""
    if not run_ids:
        return
    placeholders = ",".join("?" * len(run_ids))
    await db.execute(
        f"UPDATE pipeline_runs SET depot_repris_at = ? WHERE id IN ({placeholders})",
        [datetime.now(timezone.utc).isoformat(), *run_ids],
    )
    await db.commit()
