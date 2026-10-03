"""Runs légers d'un ticket — ticket-327.

Vérifie que `GET /projects/{id}/tickets/{ticket_id}/runs` :
- rend les runs du ticket du plus récent au plus ancien ;
- exclut les runs d'autres tickets du même projet ;
- renvoie 404 quand le ticket est inconnu.
"""
import asyncio
from pathlib import Path

import aiosqlite
import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.services.database import init_db

_TICKET_MD = """\
---
id: {id}
title: "Un ticket de test"
type: feat
status: done
priority: medium
agent: codeur
depends_on: []
---

# {id} — Un ticket de test

Body.
"""


async def _insert_run(
    db_path: Path,
    run_id: str,
    project_id: str,
    ticket_id: str,
    started_at: str,
    finished_at: str | None = None,
) -> None:
    async with aiosqlite.connect(str(db_path)) as conn:
        await conn.execute(
            "INSERT INTO pipeline_runs"
            " (id, project_id, ticket_id, started_at, finished_at, rounds, approved, final_status, mode)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (run_id, project_id, ticket_id, started_at, finished_at, 1, 1, "done", "single"),
        )
        await conn.commit()


@pytest.fixture(autouse=True)
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ws = tmp_path / "workspace"
    project = ws / "proj-alpha"
    (project / "memory").mkdir(parents=True)
    (project / "CLAUDE.md").write_text("# proj-alpha\n", encoding="utf-8")
    for st in ("todo", "in-progress", "in-review", "done", "blocked"):
        (project / "tickets" / st).mkdir(parents=True)
    (project / "tickets" / "done" / "ticket-001-slug.md").write_text(
        _TICKET_MD.format(id="ticket-001"), encoding="utf-8"
    )

    db_path = tmp_path / "tessera.db"
    asyncio.run(init_db(db_path))
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    monkeypatch.setattr(settings, "ide_db_path", db_path)
    monkeypatch.setattr(settings, "github_token", "")
    return ws


def _client() -> TestClient:
    return TestClient(app)


def test_runs_are_ordered_most_recent_first() -> None:
    """Criterion 1 — runs listed newest to oldest."""
    asyncio.run(_insert_run(
        settings.ide_db_path, "r-old", "proj-alpha", "ticket-001",
        "2026-09-01T10:00:00+00:00", "2026-09-01T10:10:00+00:00",
    ))
    asyncio.run(_insert_run(
        settings.ide_db_path, "r-new", "proj-alpha", "ticket-001",
        "2026-09-02T10:00:00+00:00", "2026-09-02T10:10:00+00:00",
    ))

    resp = _client().get("/api/v1/projects/proj-alpha/tickets/ticket-001/runs")

    assert resp.status_code == 200
    runs = resp.json()
    assert len(runs) == 2
    assert runs[0]["id"] == "r-new"
    assert runs[1]["id"] == "r-old"


def test_runs_from_other_tickets_are_excluded() -> None:
    """Only runs whose ticket_id matches are returned."""
    asyncio.run(_insert_run(
        settings.ide_db_path, "r-001", "proj-alpha", "ticket-001",
        "2026-09-01T10:00:00+00:00",
    ))
    asyncio.run(_insert_run(
        settings.ide_db_path, "r-002", "proj-alpha", "ticket-002",
        "2026-09-02T10:00:00+00:00",
    ))

    resp = _client().get("/api/v1/projects/proj-alpha/tickets/ticket-001/runs")

    assert resp.status_code == 200
    runs = resp.json()
    assert len(runs) == 1
    assert runs[0]["id"] == "r-001"


def test_unknown_ticket_returns_404() -> None:
    """A ticket that does not exist on disk → 404, not 200 with empty list."""
    resp = _client().get("/api/v1/projects/proj-alpha/tickets/ticket-999/runs")

    assert resp.status_code == 404
