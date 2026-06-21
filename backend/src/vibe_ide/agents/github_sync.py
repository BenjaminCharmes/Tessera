from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from vibe_ide.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from vibe_ide.services.github_service import GitHubIssue, GitHubService
from vibe_ide.services.sync_map import SyncEntry, SyncMapService
from vibe_ide.services.ticket_service import TicketService

_TYPE_MAP: dict[str, TicketType] = {
    "feat": TicketType.feat,
    "feature": TicketType.feat,
    "fix": TicketType.fix,
    "bug": TicketType.fix,
    "chore": TicketType.chore,
    "design": TicketType.design,
    "docs": TicketType.docs,
    "documentation": TicketType.docs,
}

_REVERSE_LABEL_MAP: dict[TicketType, str] = {
    TicketType.feat: "enhancement",
    TicketType.fix: "bug",
    TicketType.chore: "chore",
    TicketType.design: "design",
    TicketType.docs: "documentation",
}


class SyncResult(BaseModel):
    pulled: int = 0
    pushed: int = 0
    skipped: int = 0


def _extract_type(labels: list[str]) -> TicketType:
    for label in labels:
        ticket_type = _TYPE_MAP.get(label.lower())
        if ticket_type is not None:
            return ticket_type
    return TicketType.feat


def _next_ticket_n(existing_tickets: list[Ticket]) -> int:
    max_n = 0
    for t in existing_tickets:
        parts = t.id.split("-")
        if len(parts) >= 2 and parts[1].isdigit():
            max_n = max(max_n, int(parts[1]))
    return max_n + 1


class GithubSyncAgent:
    def __init__(
        self,
        github_svc: GitHubService,
        ticket_svc: TicketService,
        sync_map_svc: SyncMapService,
        project_path: Path,
        label_map: dict[str, str] | None = None,
    ) -> None:
        self._github = github_svc
        self._tickets = ticket_svc
        self._sync_map = sync_map_svc
        self._project_path = project_path
        self._label_map = label_map or {}

    async def run(
        self, direction: Literal["pull", "push", "both"] = "pull"
    ) -> SyncResult:
        sync_map = self._sync_map.load(self._project_path)
        result = SyncResult()

        if direction in ("pull", "both"):
            pulled, skipped, sync_map = await self._pull(sync_map)
            result = SyncResult(pulled=result.pulled + pulled, pushed=result.pushed, skipped=result.skipped + skipped)

        if direction in ("push", "both"):
            pushed, skipped_push, sync_map = await self._push(sync_map)
            result = SyncResult(pulled=result.pulled, pushed=result.pushed + pushed, skipped=result.skipped + skipped_push)

        self._sync_map.save(self._project_path, sync_map)
        return result

    async def _pull(
        self, sync_map: dict[str, SyncEntry]
    ) -> tuple[int, int, dict[str, SyncEntry]]:
        issues = await self._github.list_agent_ready_issues()
        all_tickets = await self._tickets.list_tickets()

        existing_urls = {t.github_issue_url for t in all_tickets if t.github_issue_url}
        existing_issue_numbers = {e.issue for e in sync_map.values() if e.issue is not None}

        pulled = 0
        skipped = 0
        next_n = _next_ticket_n(all_tickets)
        updated_map = dict(sync_map)

        for issue in issues:
            if issue.html_url in existing_urls or issue.number in existing_issue_numbers:
                skipped += 1
                continue

            ticket_id = f"ticket-{next_n:03d}"
            next_n += 1

            draft = Ticket(
                id=ticket_id,
                title=issue.title,
                type=_extract_type(issue.labels),
                status=TicketStatus.todo,
                priority=TicketPriority.medium,
                agent="orchestrateur",
                github_issue_url=issue.html_url,
                body=issue.body,
            )
            await self._tickets.create_ticket(draft)
            await self._github.remove_label(issue.number, "agent-ready")
            await self._github.add_label(issue.number, "synced-to-agent")

            updated_map[ticket_id] = SyncEntry(issue=issue.number)
            await self._log(f"PULLED: {ticket_id} ← issue #{issue.number} \"{issue.title}\"")
            pulled += 1

        return pulled, skipped, updated_map

    async def _push(
        self, sync_map: dict[str, SyncEntry]
    ) -> tuple[int, int, dict[str, SyncEntry]]:
        done_tickets = await self._tickets.list_tickets(status=TicketStatus.done)
        updated_map = dict(sync_map)
        pushed = 0
        skipped = 0

        for ticket in done_tickets:
            issue_number = self._sync_map.issue_for_ticket(updated_map, ticket.id)

            if issue_number is not None:
                await self._github.close_issue(issue_number)
                await self._log(f"CLOSED: issue #{issue_number} ← {ticket.id} \"{ticket.title}\"")
                pushed += 1
            else:
                github_label = self._label_map.get(ticket.type.value) or _REVERSE_LABEL_MAP.get(ticket.type, "")
                labels = [github_label] if github_label else []
                new_number = await self._github.create_issue(
                    title=ticket.title,
                    body=ticket.body or "",
                    labels=labels,
                )
                await self._github.close_issue(new_number)
                existing = updated_map.get(ticket.id, SyncEntry())
                updated_map[ticket.id] = SyncEntry(issue=new_number, pr=existing.pr)
                await self._log(
                    f"PUSHED+CLOSED: {ticket.id} \"{ticket.title}\" → issue #{new_number}"
                )
                pushed += 1

        return pushed, skipped, updated_map

    async def _log(self, message: str) -> None:
        log_path = self._project_path / "memory" / "github-sync-log.md"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        entry = f"- {ts} — {message}\n"
        with log_path.open("a", encoding="utf-8") as f:
            f.write(entry)
