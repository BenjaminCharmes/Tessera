"""Bulk PR status resolution — ticket-366.

Returns the PR status for every ticket that carries a pr_number, using
as few GitHub calls as possible:
- settled (merged/closed) PRs in the in-memory or DB cache are served
  without any GitHub API call;
- the remaining ones are resolved in a single paginated listing;
- CI status for open PRs is cached for OPEN_TTL seconds (30 s).
"""
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from tessera.models.ticket import Ticket
from tessera.services.github_service import GitHubService, PRStatus
from tessera.services import pr_status_cache
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)


@dataclass
class TicketPrStatus:
    """PR status entry tied to a ticket identifier."""

    ticket_id: str
    pr_number: int
    state: Literal["open", "closed", "merged"]
    ci_status: Literal["pending", "passing", "failing", "none"]
    pr_url: str


async def get_all_pr_statuses(
    db_path: Path,
    repo: str,
    github_svc: GitHubService,
    tickets: list[Ticket],
    *,
    now: Callable[[], float] = time.monotonic,
) -> list[TicketPrStatus]:
    """Return PR statuses for every ticket that carries a pr_number.

    Tickets without a pr_number are silently omitted.
    PR numbers not found in the repository are silently omitted (no error).
    """
    tickets_with_pr = [(t.id, t.pr_number) for t in tickets if t.pr_number is not None]
    if not tickets_with_pr:
        return []

    all_pr_numbers: set[int] = {pr for _, pr in tickets_with_pr}
    resolved: dict[int, PRStatus] = {}
    remaining: set[int] = set(all_pr_numbers)

    # 1. In-memory cache — covers both settled and open-within-TTL PRs
    for pr_num in all_pr_numbers:
        cached = pr_status_cache.check_memory_cache(repo, pr_num, now=now)
        if cached is not None:
            resolved[pr_num] = cached
            remaining.discard(pr_num)

    # 2. DB lookup for settled PRs not yet in memory
    if remaining:
        db_settled = await pr_status_cache.load_settled_from_db(db_path, repo, remaining)
        for pr_num, status in db_settled.items():
            resolved[pr_num] = status
            pr_status_cache.write_memory_cache(repo, pr_num, status, now=now)
            remaining.discard(pr_num)

    # 3. Single paginated listing for everything else
    if remaining:
        _logger.debug("pr_statuses_listing", extra={"count": len(remaining)})
        listing = await github_svc.list_pull_requests(remaining)
        for pr_num, entry in listing.items():
            ci: Literal["pending", "passing", "failing", "none"]
            if entry.state in ("merged", "closed"):
                ci = "none"
                status = PRStatus(
                    state=entry.state, ci_status=ci,
                    pr_url=entry.pr_url, pr_number=pr_num,
                )
                await pr_status_cache.save_settled_to_db(db_path, repo, pr_num, status)
            else:
                ci = await github_svc.get_ci_status(entry.head_sha)
                status = PRStatus(
                    state=entry.state, ci_status=ci,
                    pr_url=entry.pr_url, pr_number=pr_num,
                )
            resolved[pr_num] = status
            pr_status_cache.write_memory_cache(repo, pr_num, status, now=now)
        # PR numbers still absent from `listing` are not in the repo → omit silently

    # 4. Build the ordered result list
    return [
        TicketPrStatus(
            ticket_id=ticket_id,
            pr_number=pr_num,
            state=resolved[pr_num].state,
            ci_status=resolved[pr_num].ci_status,
            pr_url=resolved[pr_num].pr_url,
        )
        for ticket_id, pr_num in tickets_with_pr
        if pr_num in resolved
    ]
