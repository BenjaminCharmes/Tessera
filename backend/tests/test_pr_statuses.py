"""Bulk PR status endpoint — ticket-366.

Five acceptance criteria tested here:
1. Merged PRs already in the DB are returned without any GitHub call.
2. PRs absent from the DB are resolved in a single listing call; settled
   ones are then written to the DB.
3. The CI status of an open PR is queried at most once per 30-second window.
4. A pr_number absent from the GitHub listing is omitted from the response
   (status 200 with a shorter list).
5. A ticket without a pr_number is not included in the response.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import pytest

from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services import pr_status_cache
from tessera.services.database import init_db
from tessera.services.github_service import PRListEntry, PRStatus
from tessera.services.pr_statuses import get_all_pr_statuses


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _new_db(tmp_path: Path) -> Path:
    db = tmp_path / "tessera.db"
    await init_db(db)
    return db


def _ticket(ticket_id: str, pr_number: int | None = None) -> Ticket:
    return Ticket(
        id=ticket_id,
        title=f"Ticket {ticket_id}",
        type=TicketType.feat,
        status=TicketStatus.done,
        priority=TicketPriority.medium,
        agent="codeur",
        pr_number=pr_number,
    )


def _merged_entry(pr_number: int) -> PRListEntry:
    return PRListEntry(
        state="merged",
        pr_url=f"https://github.com/owner/repo/pull/{pr_number}",
        head_sha=f"sha{pr_number}",
    )


def _open_entry(pr_number: int) -> PRListEntry:
    return PRListEntry(
        state="open",
        pr_url=f"https://github.com/owner/repo/pull/{pr_number}",
        head_sha=f"sha{pr_number}",
    )


# ---------------------------------------------------------------------------
# Mock GitHub service
# ---------------------------------------------------------------------------


class MockGitHubService:
    """Minimal stand-in for GitHubService — records call counts."""

    def __init__(
        self,
        listing: dict[int, PRListEntry] | None = None,
        ci: Literal["pending", "passing", "failing", "none"] = "passing",
    ) -> None:
        self._listing: dict[int, PRListEntry] = listing or {}
        self._ci = ci
        self.listing_calls: int = 0
        self.ci_calls: int = 0

    async def list_pull_requests(self, needed: set[int]) -> dict[int, PRListEntry]:
        self.listing_calls += 1
        return {k: v for k, v in self._listing.items() if k in needed}

    async def get_ci_status(
        self, sha: str
    ) -> Literal["pending", "passing", "failing", "none"]:
        self.ci_calls += 1
        return self._ci


# ---------------------------------------------------------------------------
# Criteria 1 — merged PRs in DB returned without any GitHub call
# ---------------------------------------------------------------------------


async def test_merged_prs_in_db_no_github_call(tmp_path: Path) -> None:
    """Three merged PRs already in the DB must not trigger any GitHub call."""
    db = await _new_db(tmp_path)
    repo = "owner/repo"
    pr_numbers = [10, 11, 12]

    # Pre-populate the DB with three merged PRs
    for num in pr_numbers:
        status = PRStatus(
            state="merged",
            ci_status="passing",
            pr_url=f"https://github.com/owner/repo/pull/{num}",
            pr_number=num,
        )
        await pr_status_cache.save_settled_to_db(db, repo, num, status)

    tickets = [_ticket(f"ticket-{num:03d}", pr_number=num) for num in pr_numbers]
    gh = MockGitHubService()

    result = await get_all_pr_statuses(db, repo, gh, tickets)

    assert len(result) == 3
    assert {r.pr_number for r in result} == set(pr_numbers)
    assert all(r.state == "merged" for r in result)
    assert gh.listing_calls == 0
    assert gh.ci_calls == 0


# ---------------------------------------------------------------------------
# Criteria 2 — PRs absent from DB resolved in one listing call; saved to DB
# ---------------------------------------------------------------------------


async def test_missing_prs_use_single_listing_call(tmp_path: Path) -> None:
    """Three PRs not in the DB must be resolved in exactly one listing call."""
    db = await _new_db(tmp_path)
    repo = "owner/repo"
    pr_numbers = [20, 21, 22]

    tickets = [_ticket(f"ticket-{n:03d}", pr_number=n) for n in pr_numbers]
    listing = {n: _merged_entry(n) for n in pr_numbers}
    gh = MockGitHubService(listing=listing)

    result = await get_all_pr_statuses(db, repo, gh, tickets)

    assert len(result) == 3
    assert gh.listing_calls == 1
    assert gh.ci_calls == 0  # all merged → no CI check

    # Settled PRs must now be persisted in the DB
    db_statuses = await pr_status_cache.load_settled_from_db(db, repo, set(pr_numbers))
    assert set(db_statuses.keys()) == set(pr_numbers)
    assert all(s.state == "merged" for s in db_statuses.values())


# ---------------------------------------------------------------------------
# Criteria 3 — open PR CI queried at most once per 30-second window
# ---------------------------------------------------------------------------


async def test_open_pr_ci_cached_for_30s(tmp_path: Path) -> None:
    """CI check-runs for an open PR must not be called more than once per TTL.

    Simulated clock: call at t=0 populates the cache; call at t=20 s hits the
    cache (no CI query); call at t=31 s finds the TTL expired and re-queries.
    """
    db = await _new_db(tmp_path)
    repo = "owner/repo"
    pr_num = 30

    fake_time = 0.0

    def now() -> float:
        return fake_time

    listing = {pr_num: _open_entry(pr_num)}
    gh = MockGitHubService(listing=listing, ci="pending")
    ticket = [_ticket("ticket-030", pr_number=pr_num)]

    # Call 1 (t=0) — listing + CI, result stored in memory at t=0
    result1 = await get_all_pr_statuses(db, repo, gh, ticket, now=now)
    assert len(result1) == 1
    assert result1[0].ci_status == "pending"
    assert gh.ci_calls == 1

    # Call 2 (t=20 s) — within TTL, memory cache serves the result
    fake_time = 20.0
    result2 = await get_all_pr_statuses(db, repo, gh, ticket, now=now)
    assert len(result2) == 1
    assert gh.ci_calls == 1  # no additional CI query within the 30-second window

    # Call 3 (t=31 s) — TTL expired, listing + CI requested again
    fake_time = 31.0
    result3 = await get_all_pr_statuses(db, repo, gh, ticket, now=now)
    assert len(result3) == 1
    assert gh.ci_calls == 2


# ---------------------------------------------------------------------------
# Criteria 4 — pr_number absent from listing omitted, response is 200
# ---------------------------------------------------------------------------


async def test_pr_not_in_listing_omitted(tmp_path: Path) -> None:
    """A pr_number not found in the GitHub listing is silently omitted."""
    db = await _new_db(tmp_path)
    repo = "owner/repo"

    gh = MockGitHubService(listing={})  # listing returns nothing
    tickets = [_ticket("ticket-040", pr_number=40)]

    result = await get_all_pr_statuses(db, repo, gh, tickets)

    assert result == []
    assert gh.listing_calls == 1  # one attempt was made


# ---------------------------------------------------------------------------
# Criteria 5 — ticket without pr_number not in response
# ---------------------------------------------------------------------------


async def test_ticket_without_pr_number_not_in_response(tmp_path: Path) -> None:
    """Tickets that have no pr_number must be silently excluded."""
    db = await _new_db(tmp_path)
    repo = "owner/repo"

    gh = MockGitHubService()
    tickets = [
        _ticket("ticket-050", pr_number=None),
        _ticket("ticket-051", pr_number=None),
    ]

    result = await get_all_pr_statuses(db, repo, gh, tickets)

    assert result == []
    assert gh.listing_calls == 0
