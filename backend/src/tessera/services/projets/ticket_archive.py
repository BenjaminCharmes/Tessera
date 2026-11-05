"""Archive of done tickets, filed by hundreds under `tickets/archive/done/`."""
import re
from collections.abc import Iterator
from pathlib import Path

from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: A ticket is archived once its number is this far below the highest one.
ARCHIVE_MARGIN = 100

_NUMBER_RE = re.compile(r"^ticket-(\d+)(?:-|$)")


def ticket_number(path: Path) -> int | None:
    """The number in a ticket file name (`ticket-612-x.md` -> 612), if any."""
    matched = _NUMBER_RE.match(path.stem)
    return int(matched.group(1)) if matched else None


def hundred_folder(number: int) -> str:
    """The folder holding `number`: 612 -> `600-699`."""
    start = number // 100 * 100
    return f"{start:03d}-{start + 99:03d}"


def iter_archive_files(tickets_root: Path) -> Iterator[Path]:
    """Every ticket file under `tickets/archive/`, whatever its sub-folder."""
    archive_root = tickets_root / "archive"
    if archive_root.is_dir():
        yield from sorted(archive_root.rglob("ticket-*.md"))


def is_archived(path: Path) -> bool:
    """Whether `path` sits in `archive/done/<folder>/`."""
    return path.parent.parent.name == "done" and path.parent.parent.parent.name == "archive"


def highest_number(tickets_root: Path) -> int:
    """The highest ticket number under `tickets/`, archive included (0 if none)."""
    if not tickets_root.is_dir():
        return 0
    numbers = (ticket_number(p) for p in tickets_root.rglob("ticket-*.md"))
    return max((n for n in numbers if n is not None), default=0)


def archive_done_tickets(tickets_root: Path, margin: int = ARCHIVE_MARGIN) -> list[str]:
    """Move done tickets at least `margin` below the highest number into the archive.

    Returns the ids archived, in order. A ticket whose destination already
    exists stays where it is: overwriting would lose one of the two copies.
    """
    done_dir = tickets_root / "done"
    if not done_dir.is_dir():
        return []
    limit = highest_number(tickets_root) - margin
    archived: list[str] = []
    for path in sorted(done_dir.glob("ticket-*.md")):
        number = ticket_number(path)
        if number is None or number > limit:
            continue
        dest_dir = tickets_root / "archive" / "done" / hundred_folder(number)
        dest = dest_dir / path.name
        if dest.exists():
            _logger.warning("ticket_archive_collision", extra={"path": str(path)})
            continue
        dest_dir.mkdir(parents=True, exist_ok=True)
        path.replace(dest)
        archived.append(f"ticket-{path.stem.split('-')[1]}")  # garde le zéro de tête
    return archived
