import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import frontmatter  # type: ignore[import-untyped]

from vibe_ide.models.ticket import Ticket, TicketStatus


_STATUS_DIRS = {
    TicketStatus.todo: "todo",
    TicketStatus.in_progress: "in-progress",
    TicketStatus.done: "done",
    TicketStatus.cancelled: "cancelled",
}


def _tickets_root(project_path: Path) -> Path:
    return project_path / "tickets"


def _iter_ticket_files(project_path: Path) -> Iterator[Path]:
    root = _tickets_root(project_path)
    if not root.is_dir():
        return
    for status_dir in root.iterdir():
        if status_dir.is_dir():
            yield from sorted(status_dir.glob("ticket-*.md"))


def list_tickets(project_path: Path) -> list[Ticket]:
    """Retourne tous les tickets d'un projet."""
    tickets: list[Ticket] = []
    for path in _iter_ticket_files(project_path):
        try:
            tickets.append(_parse_ticket(path))
        except Exception:
            continue
    return sorted(tickets, key=lambda t: t.id)


def get_ticket(project_path: Path, ticket_id: str) -> Ticket | None:
    """Retourne un ticket par son id, ou None."""
    for path in _iter_ticket_files(project_path):
        if path.stem.startswith(ticket_id):
            return _parse_ticket(path)
    return None


def update_ticket_status(
    project_path: Path, ticket_id: str, new_status: TicketStatus
) -> Ticket:
    """Déplace le fichier ticket dans le bon dossier de statut."""
    ticket = get_ticket(project_path, ticket_id)
    if ticket is None:
        raise ValueError(f"Ticket introuvable : {ticket_id}")

    # Trouver le fichier source
    source_path: Path | None = None
    for path in _iter_ticket_files(project_path):
        if path.stem.startswith(ticket_id):
            source_path = path
            break

    if source_path is None:
        raise ValueError(f"Fichier ticket introuvable : {ticket_id}")

    dest_dir = _tickets_root(project_path) / _STATUS_DIRS[new_status]
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / source_path.name

    if source_path != dest_path:
        source_path.rename(dest_path)

    # Mettre à jour le frontmatter
    post = frontmatter.load(str(dest_path))
    post["status"] = new_status.value
    with dest_path.open("w", encoding="utf-8") as f:
        f.write(frontmatter.dumps(post))

    return _parse_ticket(dest_path)


def archive_old_tickets(project_path: Path, days: int = 30) -> list[Ticket]:
    """Déplace les tickets done/ plus anciens que `days` jours vers archive/done/YYYY-MM/."""
    done_dir = _tickets_root(project_path) / "done"
    if not done_dir.is_dir():
        return []

    cutoff = time.time() - days * 86400
    archived: list[Ticket] = []

    for ticket_file in sorted(done_dir.glob("ticket-*.md")):
        if ticket_file.stat().st_mtime > cutoff:
            continue
        mtime = datetime.fromtimestamp(ticket_file.stat().st_mtime, tz=timezone.utc)
        dest_dir = _tickets_root(project_path) / "archive" / "done" / mtime.strftime("%Y-%m")
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / ticket_file.name
        ticket_file.rename(dest_path)
        try:
            archived.append(_parse_ticket(dest_path))
        except Exception:
            pass

    return archived


def list_archived_tickets(project_path: Path) -> list[Ticket]:
    """Retourne tous les tickets archivés."""
    archive_root = _tickets_root(project_path) / "archive"
    if not archive_root.is_dir():
        return []

    tickets: list[Ticket] = []
    for ticket_file in sorted(archive_root.rglob("ticket-*.md")):
        try:
            tickets.append(_parse_ticket(ticket_file))
        except Exception:
            continue
    return tickets


_PIPELINE_LOG_MAX_LINES = 200


def rotate_pipeline_log(project_path: Path) -> None:
    """Tronque pipeline-log.md à _PIPELINE_LOG_MAX_LINES lignes (garde les plus récentes)."""
    log_path = project_path / "pipeline-log.md"
    if not log_path.exists():
        return

    lines = log_path.read_text(encoding="utf-8").splitlines(keepends=True)
    if len(lines) <= _PIPELINE_LOG_MAX_LINES:
        return

    log_path.write_text("".join(lines[-_PIPELINE_LOG_MAX_LINES:]), encoding="utf-8")


def _parse_ticket(path: Path) -> Ticket:
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
        github_issue_url=meta.get("github_issue_url") or None,
        body=str(post.content),
    )
