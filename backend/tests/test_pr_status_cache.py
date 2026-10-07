"""PR status cache — ticket-364.

Four acceptance criteria tested here:
- Two calls for a merged PR only contact GitHub once (in-memory cache).
- A merged PR already recorded in the DB is served without a GitHub call
  after the in-memory cache is cleared (SQLite persistence).
- An open PR is re-queried after 30 s (simulated clock) but not before.
- A 404 from GitHub is not cached.
"""
from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from tessera.services import pr_status_cache
from tessera.services.database import init_db
from tessera.services.github_service import PRStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _merged(pr_number: int = 1) -> PRStatus:
    return PRStatus(
        state="merged",
        ci_status="passing",
        pr_url=f"https://github.com/owner/repo/pull/{pr_number}",
        pr_number=pr_number,
    )


def _open(pr_number: int = 3) -> PRStatus:
    return PRStatus(
        state="open",
        ci_status="pending",
        pr_url=f"https://github.com/owner/repo/pull/{pr_number}",
        pr_number=pr_number,
    )


def _make_404() -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://api.github.com/repos/owner/repo/pulls/99")
    response = httpx.Response(404, request=request)
    return httpx.HTTPStatusError("Not Found", request=request, response=response)


async def _new_db(tmp_path: Path) -> Path:
    db = tmp_path / "tessera.db"
    await init_db(db)
    return db


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_merged_pr_calls_github_only_once(tmp_path: Path) -> None:
    """Two successive calls for a merged PR must not contact GitHub twice."""
    db = await _new_db(tmp_path)
    call_count = 0

    async def fetch() -> PRStatus:
        nonlocal call_count
        call_count += 1
        return _merged(1)

    await pr_status_cache.get_cached_status(db, "owner/repo", 1, fetch)
    result = await pr_status_cache.get_cached_status(db, "owner/repo", 1, fetch)

    assert result.state == "merged"
    assert call_count == 1


async def test_merged_pr_served_from_db_after_memory_cleared(tmp_path: Path) -> None:
    """A merged PR already in the DB is served without calling GitHub
    even after the in-memory cache has been flushed (simulates a restart)."""
    db = await _new_db(tmp_path)
    call_count = 0

    async def fetch() -> PRStatus:
        nonlocal call_count
        call_count += 1
        return _merged(2)

    # First call: goes through GitHub, writes to DB and memory
    result1 = await pr_status_cache.get_cached_status(db, "owner/repo", 2, fetch)
    assert result1.state == "merged"
    assert call_count == 1

    # Simulate backend restart: flush in-memory cache
    pr_status_cache.clear_memory_cache()

    # Second call: must be served from SQLite without contacting GitHub
    result2 = await pr_status_cache.get_cached_status(db, "owner/repo", 2, fetch)
    assert result2.state == "merged"
    assert result2.pr_number == 2
    assert call_count == 1  # no additional GitHub call


async def test_open_pr_re_queried_after_ttl(tmp_path: Path) -> None:
    """An open PR is cached for 30 s then re-queried; before that, cached."""
    db = await _new_db(tmp_path)
    call_count = 0
    fake_time = 0.0

    def now() -> float:
        return fake_time

    async def fetch() -> PRStatus:
        nonlocal call_count
        call_count += 1
        return _open(3)

    # First call — GitHub contacted
    await pr_status_cache.get_cached_status(db, "owner/repo", 3, fetch, now=now)
    assert call_count == 1

    # Within TTL — no additional GitHub call
    fake_time = 20.0
    await pr_status_cache.get_cached_status(db, "owner/repo", 3, fetch, now=now)
    assert call_count == 1

    # After TTL expires — GitHub contacted again
    fake_time = 31.0
    result = await pr_status_cache.get_cached_status(db, "owner/repo", 3, fetch, now=now)
    assert result.state == "open"
    assert call_count == 2


async def test_github_404_not_cached(tmp_path: Path) -> None:
    """A 404 from GitHub must not be cached; next call must hit GitHub again."""
    db = await _new_db(tmp_path)
    call_count = 0

    async def fetch_404() -> PRStatus:
        nonlocal call_count
        call_count += 1
        raise _make_404()

    # First call — raises, not cached
    with pytest.raises(httpx.HTTPStatusError):
        await pr_status_cache.get_cached_status(db, "owner/repo", 99, fetch_404)
    assert call_count == 1

    # Second call — GitHub must be called again (no cache entry)
    with pytest.raises(httpx.HTTPStatusError):
        await pr_status_cache.get_cached_status(db, "owner/repo", 99, fetch_404)
    assert call_count == 2
