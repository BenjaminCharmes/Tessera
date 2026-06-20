import os
import time
from pathlib import Path

import frontmatter  # type: ignore[import-untyped]
import pytest

from vibe_ide.services.ticket_service import (
    archive_old_tickets,
    list_archived_tickets,
    rotate_pipeline_log,
)


def _write_ticket(path: Path, ticket_id: str, status: str = "done") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    post = frontmatter.Post(
        content="Corps du ticket.",
        id=ticket_id,
        title=f"Ticket {ticket_id}",
        type="chore",
        status=status,
        priority="medium",
        agent="codeur",
    )
    path.write_text(frontmatter.dumps(post), encoding="utf-8")


def _age_file(path: Path, seconds: int) -> None:
    ts = time.time() - seconds
    os.utime(path, (ts, ts))


# --- archive_old_tickets ---


def test_archive_moves_old_done_tickets(tmp_path: Path) -> None:
    ticket_path = tmp_path / "tickets" / "done" / "ticket-001-old.md"
    _write_ticket(ticket_path, "ticket-001")
    _age_file(ticket_path, 31 * 86400)

    archived = archive_old_tickets(tmp_path, days=30)

    assert len(archived) == 1
    assert archived[0].id == "ticket-001"
    assert not ticket_path.exists()
    assert any((tmp_path / "tickets" / "archive").rglob("ticket-001-old.md"))


def test_archive_keeps_recent_tickets(tmp_path: Path) -> None:
    ticket_path = tmp_path / "tickets" / "done" / "ticket-002-new.md"
    _write_ticket(ticket_path, "ticket-002")

    archived = archive_old_tickets(tmp_path, days=30)

    assert archived == []
    assert ticket_path.exists()


def test_archive_no_done_dir(tmp_path: Path) -> None:
    assert archive_old_tickets(tmp_path) == []


# --- list_archived_tickets ---


def test_list_archived_tickets_empty(tmp_path: Path) -> None:
    assert list_archived_tickets(tmp_path) == []


def test_list_archived_tickets_returns_archived(tmp_path: Path) -> None:
    archive_path = tmp_path / "tickets" / "archive" / "done" / "2025-01" / "ticket-005-x.md"
    _write_ticket(archive_path, "ticket-005")

    result = list_archived_tickets(tmp_path)

    assert len(result) == 1
    assert result[0].id == "ticket-005"


# --- rotate_pipeline_log ---


def test_rotate_pipeline_log_no_file(tmp_path: Path) -> None:
    rotate_pipeline_log(tmp_path)  # ne doit pas lever d'exception


def test_rotate_pipeline_log_short_file(tmp_path: Path) -> None:
    log = tmp_path / "pipeline-log.md"
    log.write_text("\n".join(f"line {i}" for i in range(50)))
    original = log.read_text()

    rotate_pipeline_log(tmp_path)

    assert log.read_text() == original


def test_rotate_pipeline_log_truncates_to_200(tmp_path: Path) -> None:
    log = tmp_path / "pipeline-log.md"
    lines = [f"line {i}\n" for i in range(300)]
    log.write_text("".join(lines))

    rotate_pipeline_log(tmp_path)

    result_lines = log.read_text().splitlines()
    assert len(result_lines) == 200
    assert result_lines[0] == "line 100"
    assert result_lines[-1] == "line 299"
