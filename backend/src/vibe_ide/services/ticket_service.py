import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import frontmatter  # type: ignore[import-untyped]

from vibe_ide.models.ticket import Ticket, TicketDraftPlan, TicketStatus


_STATUS_DIRS: dict[TicketStatus, str] = {
    TicketStatus.todo: "todo",
    TicketStatus.in_progress: "in-progress",
    TicketStatus.in_review: "in-review",
    TicketStatus.done: "done",
    TicketStatus.blocked: "blocked",
    TicketStatus.cancelled: "cancelled",
}

_PIPELINE_LOG_MAX_LINES = 200


def _slugify(text: str, max_len: int = 40) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[\s_]+", "-", slug)
    return slug[:max_len].rstrip("-")


class TicketService:
    def __init__(self, project_path: Path, project_id: str) -> None:
        self._root = project_path
        self._project_id = project_id

    # ------------------------------------------------------------------
    # Public async API
    # ------------------------------------------------------------------

    async def list_tickets(
        self, status: TicketStatus | None = None
    ) -> list[Ticket]:
        tickets: list[Ticket] = []
        for path in self._iter_active_files():
            try:
                t = self._parse(path)
                if status is None or t.status == status:
                    tickets.append(t)
            except Exception:
                continue
        return sorted(tickets, key=lambda t: t.id)

    async def get_ticket(self, ticket_id: str) -> Ticket | None:
        for path in self._iter_active_files():
            if path.stem.startswith(ticket_id):
                return self._parse(path)
        return None

    async def update_status(
        self, ticket_id: str, new_status: TicketStatus
    ) -> Ticket:
        source = self._find_file(ticket_id)
        if source is None:
            raise ValueError(f"Ticket introuvable : {ticket_id}")

        dest_dir = self._tickets_root() / _STATUS_DIRS[new_status]
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / source.name

        if source != dest:
            source.rename(dest)

        post = frontmatter.load(str(dest))
        post["status"] = new_status.value
        dest.write_text(frontmatter.dumps(post), encoding="utf-8")
        return self._parse(dest)

    async def create_ticket(self, ticket: Ticket) -> Ticket:
        ticket_id = ticket.id if ticket.id else self._next_id()
        created = ticket.created or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        dest_dir = self._tickets_root() / "todo"
        dest_dir.mkdir(parents=True, exist_ok=True)

        slug = _slugify(ticket.title)
        dest = dest_dir / f"{ticket_id}-{slug}.md"

        post = frontmatter.Post(
            content=ticket.body,
            id=ticket_id,
            title=ticket.title,
            type=ticket.type.value,
            status=TicketStatus.todo.value,
            priority=ticket.priority.value,
            agent=ticket.agent,
            depends_on=ticket.depends_on,
            created=created,
        )
        if ticket.github_issue_url:
            post["github_issue_url"] = ticket.github_issue_url

        dest.write_text(frontmatter.dumps(post), encoding="utf-8")
        return self._parse(dest)

    async def create_tickets_batch(self, drafts: list[TicketDraftPlan]) -> list[Ticket]:
        if not drafts:
            return []
        base_n = self._next_n()
        ids = [f"ticket-{base_n + i:03d}" for i in range(len(drafts))]

        created: list[Ticket] = []
        for i, draft in enumerate(drafts):
            depends_on = [
                ids[dep_idx]
                for dep_idx in draft.depends_on_index
                if 0 <= dep_idx < len(ids)
            ]
            ticket = Ticket(
                id=ids[i],
                title=draft.title,
                type=draft.type,
                status=TicketStatus.todo,
                priority=draft.priority,
                agent=draft.agent,
                depends_on=depends_on,
                body=draft.description,
            )
            created.append(await self.create_ticket(ticket))
        return created

    async def archive_old_tickets(self, days: int = 30) -> list[Ticket]:
        done_dir = self._tickets_root() / "done"
        if not done_dir.is_dir():
            return []

        cutoff = time.time() - days * 86400
        archived: list[Ticket] = []

        for ticket_file in sorted(done_dir.glob("ticket-*.md")):
            if ticket_file.stat().st_mtime > cutoff:
                continue
            mtime = datetime.fromtimestamp(
                ticket_file.stat().st_mtime, tz=timezone.utc
            )
            dest_dir = (
                self._tickets_root()
                / "archive"
                / "done"
                / mtime.strftime("%Y-%m")
            )
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / ticket_file.name
            ticket_file.rename(dest)
            try:
                archived.append(self._parse(dest))
            except Exception:
                pass

        return archived

    async def list_archived_tickets(self) -> list[Ticket]:
        archive_root = self._tickets_root() / "archive"
        if not archive_root.is_dir():
            return []
        tickets: list[Ticket] = []
        for path in sorted(archive_root.rglob("ticket-*.md")):
            try:
                tickets.append(self._parse(path))
            except Exception:
                continue
        return tickets

    async def set_pr_number(self, ticket_id: str, pr_number: int) -> Ticket:
        source = self._find_file(ticket_id)
        if source is None:
            raise ValueError(f"Ticket introuvable : {ticket_id}")
        post = frontmatter.load(str(source))
        post["pr_number"] = pr_number
        source.write_text(frontmatter.dumps(post), encoding="utf-8")
        return self._parse(source)

    async def rotate_pipeline_log(self) -> None:
        log_path = self._root / "pipeline-log.md"
        if not log_path.exists():
            return
        lines = log_path.read_text(encoding="utf-8").splitlines(keepends=True)
        if len(lines) > _PIPELINE_LOG_MAX_LINES:
            log_path.write_text(
                "".join(lines[-_PIPELINE_LOG_MAX_LINES:]), encoding="utf-8"
            )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _tickets_root(self) -> Path:
        return self._root / "tickets"

    def _iter_active_files(self) -> Iterator[Path]:
        root = self._tickets_root()
        if not root.is_dir():
            return
        for status_dir in sorted(root.iterdir()):
            if not status_dir.is_dir() or status_dir.name == "archive":
                continue
            yield from sorted(status_dir.glob("ticket-*.md"))

    def _find_file(self, ticket_id: str) -> Path | None:
        for path in self._iter_active_files():
            if path.stem.startswith(ticket_id):
                return path
        return None

    def _next_n(self) -> int:
        max_n = 0
        root = self._tickets_root()
        if root.is_dir():
            for path in root.rglob("ticket-*.md"):
                parts = path.stem.split("-")
                if len(parts) >= 2 and parts[1].isdigit():
                    max_n = max(max_n, int(parts[1]))
        return max_n + 1

    def _next_id(self) -> str:
        return f"ticket-{self._next_n():03d}"

    def _parse(self, path: Path) -> Ticket:
        post = frontmatter.load(str(path))
        meta = post.metadata
        return Ticket(
            id=str(meta["id"]),
            title=str(meta["title"]),
            type=meta["type"],
            status=meta["status"],
            priority=meta["priority"],
            agent=str(meta["agent"]),
            depends_on=list(meta.get("depends_on", [])),
            created=str(meta.get("created", "")),
            github_issue_url=meta.get("github_issue_url") or None,
            pr_number=int(meta["pr_number"]) if isinstance(meta.get("pr_number"), int) else None,
            body=str(post.content),
            project_id=self._project_id,
            file_path=str(path),
        )
