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
        body=str(post.content),
    )
