import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import frontmatter

from tessera.models.ticket import (
    Ticket,
    TicketDraftPlan,
    TicketPriority,
    TicketStatus,
    TicketType,
    TicketUnreadable,
)
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)


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


_TICKET_ID_RE = re.compile(r"^ticket-\d+$")


def _normalize_depends_on(raw: object) -> list[str]:
    """Coerce any YAML representation of depends_on into a list of ticket ids.

    YAML scalars like ``depends_on: ticket-001`` reach Python as a plain string.
    Iterating over a string yields characters, not ticket ids — the root cause
    of ticket-275.  This function handles all three forms:

    * ``None`` / empty string / empty list → ``[]``
    * ``str`` → split on commas, strip whitespace, discard empty pieces
    * ``list`` → kept as-is after coercion to str

    Items that do not look like ``ticket-NNN`` are discarded and logged.
    """
    if not raw:
        return []

    if isinstance(raw, str):
        pieces = [part.strip() for part in raw.split(",")]
    elif isinstance(raw, (list, tuple)):
        pieces = [str(item) for item in raw]
    else:
        pieces = [str(raw)]

    result: list[str] = []
    for piece in pieces:
        if not piece:
            continue
        if _TICKET_ID_RE.match(piece):
            result.append(piece)
        else:
            _logger.warning(
                "depends_on_invalid_id",
                extra={"value": piece},
            )
    return result


def _status_from_folder(path: Path, meta: dict[str, Any]) -> TicketStatus:
    """Le dossier fait foi ; le frontmatter n'est qu'un repli.

    C'est le service qui place les fichiers dans `_STATUS_DIRS` : le dossier ne
    peut pas mentir sur ce qu'il a fait. Le champ frontmatter, lui, dérive dès
    qu'un fichier est écrit sans être mis à jour — douze tickets de `ide-core`
    étaient dans `done/` en annonçant `status: todo`, et l'UI les affichait
    comme à faire (ticket-059).

    Le champ reste écrit dans le fichier pour qu'il se lise seul, hors de
    l'IDE : il est dérivé, pas autoritaire.
    """
    by_dir = {directory: status for status, directory in _STATUS_DIRS.items()}
    folder_status = by_dir.get(path.parent.name)
    if folder_status is not None:
        return folder_status
    # Dossier non reconnu (archive, arborescence inattendue) : on retombe sur
    # ce que le fichier déclare plutôt que d'échouer.
    return TicketStatus(meta["status"])


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
        """Return parseable tickets, logging unreadable files without raising."""
        tickets, _ = await self.list_tickets_with_unreadable(status)
        return tickets

    async def list_tickets_with_unreadable(
        self, status: TicketStatus | None = None
    ) -> tuple[list[Ticket], list[TicketUnreadable]]:
        """Return parseable tickets and files that could not be parsed."""
        tickets: list[Ticket] = []
        unreadable: list[TicketUnreadable] = []
        for path in self._iter_active_files():
            try:
                t = self._parse(path)
                if status is None or t.status == status:
                    tickets.append(t)
            except Exception as exc:
                _logger.warning(
                    "ticket_unreadable",
                    extra={"path": str(path), "error": str(exc)},
                )
                unreadable.append(
                    TicketUnreadable(file_path=str(path), error=str(exc))
                )
        return sorted(tickets, key=lambda t: t.id), unreadable

    async def get_ticket(self, ticket_id: str) -> Ticket | None:
        path = self._find_file(ticket_id)
        return self._parse(path) if path is not None else None

    async def update_status(
        self, ticket_id: str, new_status: TicketStatus
    ) -> Ticket:
        sources = self._find_all_files(ticket_id)
        if not sources:
            raise ValueError(f"Ticket introuvable : {ticket_id}")

        dest_dir = self._tickets_root() / _STATUS_DIRS[new_status]
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / sources[0].name

        # Move one copy to the destination; delete any extra copies.
        # `replace` is used instead of `rename` because on Windows `rename`
        # raises `FileExistsError` when the destination already exists.
        # Duplicates arise when a branch is resumed: the base branch holds
        # the ticket in `todo/` and the ticket branch holds it in `blocked/`,
        # and the `set_status` call runs after the branch switch so both
        # copies are momentarily visible (ticket-220).
        moved = False
        for source in sources:
            if source == dest:
                moved = True
                continue
            if not moved:
                source.replace(dest)
                moved = True
            else:
                source.unlink()

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
                # `TicketDraftPlan` carries the planner's raw strings; the
                # enums are the persisted contract, so coerce here rather
                # than letting an invalid value reach the ticket file.
                type=TicketType(draft.type),
                status=TicketStatus.todo,
                priority=TicketPriority(draft.priority),
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

    async def rotate_pipeline_log(self, log_path: Path | None = None) -> None:
        """Keep the pipeline log to its last `_PIPELINE_LOG_MAX_LINES` lines.

        Le défaut est le fichier que l'orchestrateur écrit réellement,
        `memory/pipeline-log.md` ; la rotation lisait `<projet>/pipeline-log.md`
        et ne tournait donc jamais (ticket-122). L'appelant qui connaît le
        chemin peut le transmettre.
        """
        if log_path is None:
            log_path = self._root / "memory" / "pipeline-log.md"
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
        # `stem.startswith(ticket_id)` faisait trouver `ticket-100` à partir de
        # `ticket-1` (ticket-122). Le nom est l'identifiant seul, ou
        # l'identifiant suivi d'un tiret et d'un slug.
        for path in self._iter_active_files():
            if path.stem == ticket_id or path.stem.startswith(ticket_id + "-"):
                return path
        return None

    def _find_all_files(self, ticket_id: str) -> list[Path]:
        """Return every active file matching `ticket_id`, across all status folders.

        More than one result means a branch resume left a stale copy in another
        folder (ticket-220).  `update_status` uses this list to consolidate them.
        """
        return [
            path
            for path in self._iter_active_files()
            if path.stem == ticket_id or path.stem.startswith(ticket_id + "-")
        ]

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
        # Frontmatter metadata is arbitrary YAML: every field is coerced to
        # the model's own type here, at the parsing boundary, so an invalid
        # ticket file fails loudly instead of producing a half-typed Ticket.
        meta: dict[str, Any] = dict(post.metadata)
        raw_pr_number = meta.get("pr_number")
        return Ticket(
            id=str(meta["id"]),
            title=str(meta["title"]),
            type=TicketType(meta["type"]),
            status=_status_from_folder(path, meta),
            priority=TicketPriority(meta["priority"]),
            agent=str(meta["agent"]),
            depends_on=_normalize_depends_on(meta.get("depends_on")),
            created=str(meta.get("created", "")),
            github_issue_url=str(meta["github_issue_url"])
            if meta.get("github_issue_url")
            else None,
            pr_number=int(raw_pr_number) if isinstance(raw_pr_number, int) else None,
            # Seul un vrai booléen YAML l'active : « oui » ne demande rien.
            plan=meta.get("plan") is True,
            light=meta.get("light") is True,
            body=str(post.content),
            project_id=self._project_id,
            file_path=str(path),
        )
