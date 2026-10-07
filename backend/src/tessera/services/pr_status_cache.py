from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from pathlib import Path

import aiosqlite

from tessera.services.github_service import PRStatus
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

# In-memory cache: (repo, pr_number) -> (status, monotonic_timestamp)
_memory: dict[tuple[str, int], tuple[PRStatus, float]] = {}

#: A PR that is open is re-queried after this many seconds.
OPEN_TTL: float = 30.0


def clear_memory_cache() -> None:
    """Empty the in-memory cache — useful in tests and on startup."""
    _memory.clear()


async def get_cached_status(
    db_path: Path | str,
    repo: str,
    pr_number: int,
    fetch: Callable[[], Awaitable[PRStatus]],
    *,
    now: Callable[[], float] = time.monotonic,
) -> PRStatus:
    """Return PR status, served from cache when possible.

    Stratégie :
    - merged/closed en mémoire → retourné immédiatement sans I/O.
    - merged/closed en base → retourné sans appel GitHub (survive aux
      redémarrages du backend).
    - open en mémoire et dans les délais TTL → retourné sans appel GitHub.
    - Sinon : appel GitHub via `fetch`. Les 404 et les erreurs remontent
      tels quels et ne sont jamais mis en cache.
    """
    key = (repo, pr_number)

    # Check in-memory cache first
    if key in _memory:
        cached, ts = _memory[key]
        if cached.state in ("merged", "closed"):
            return cached
        if now() - ts < OPEN_TTL:
            return cached
        # Open PR TTL expired — fall through to fresh fetch

    # Check SQLite for a persisted merged/closed entry
    db_status = await _load_from_db(db_path, repo, pr_number)
    if db_status is not None:
        _memory[key] = (db_status, now())
        return db_status

    # Fetch from GitHub — 404/errors propagate unchanged, never cached
    status = await fetch()

    if status.state in ("merged", "closed"):
        await _save_to_db(db_path, repo, pr_number, status)

    _memory[key] = (status, now())
    return status


async def _load_from_db(
    db_path: Path | str, repo: str, pr_number: int
) -> PRStatus | None:
    """Load a definitive (merged/closed) status entry from the database."""
    async with aiosqlite.connect(str(db_path)) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT state, ci_status, pr_url"
            " FROM pr_status_cache"
            " WHERE repo = ? AND pr_number = ?",
            (repo, pr_number),
        ) as cursor:
            row = await cursor.fetchone()
    if row is None:
        return None
    return PRStatus(
        state=row["state"],
        ci_status=row["ci_status"],
        pr_url=row["pr_url"],
        pr_number=pr_number,
    )


async def _save_to_db(
    db_path: Path | str, repo: str, pr_number: int, status: PRStatus
) -> None:
    """Persist a definitive (merged/closed) PR status to the database."""
    async with aiosqlite.connect(str(db_path)) as db:
        await db.execute(
            """INSERT INTO pr_status_cache (repo, pr_number, state, ci_status, pr_url)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT (repo, pr_number) DO UPDATE
               SET state     = excluded.state,
                   ci_status = excluded.ci_status,
                   pr_url    = excluded.pr_url""",
            (repo, pr_number, status.state, status.ci_status, status.pr_url),
        )
        await db.commit()
