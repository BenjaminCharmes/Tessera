"""Events endpoint for finished runs — ticket-280.

Acceptance criteria:
- GET /api/v1/runs/{id}/events returns events in ts order
- agent_token events are excluded
- 404 on unknown run_id
- run_closed carries db_run_id
- a ticket played in a queue returns its own events via its row's id
"""
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.services.database import (
    create_run,
    finish_run,
    get_run_events,
    init_db,
    list_runs,
    save_event,
)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "tessera.db"


@pytest.fixture(autouse=True)
def _use_tmp_db(db_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ide_db_path", db_path)


# ---------------------------------------------------------------------------
# Database-level unit tests
# ---------------------------------------------------------------------------


async def test_get_run_events_returns_events_in_ts_order(db_path: Path) -> None:
    await init_db(db_path)
    run_id = await create_run(db_path, "project-1", "ticket-001")

    await save_event(db_path, run_id, "agent_started", "codeur",
                     {"round": 1}, "2026-10-01T10:00:01+00:00", ticket_id="ticket-001")
    await save_event(db_path, run_id, "agent_done", "codeur",
                     {"cost_usd": 0.01}, "2026-10-01T10:00:03+00:00", ticket_id="ticket-001")
    await save_event(db_path, run_id, "pipeline_done", None,
                     {"approved": True}, "2026-10-01T10:00:02+00:00", ticket_id="ticket-001")

    events = await get_run_events(db_path, run_id)
    assert events is not None
    assert [e["type"] for e in events] == [
        "agent_started", "pipeline_done", "agent_done"
    ]


async def test_get_run_events_excludes_agent_token(db_path: Path) -> None:
    await init_db(db_path)
    run_id = await create_run(db_path, "project-1", "ticket-001")

    await save_event(db_path, run_id, "agent_token", "codeur",
                     {"token": "hello"}, "2026-10-01T10:00:00+00:00", ticket_id="ticket-001")
    await save_event(db_path, run_id, "agent_done", "codeur",
                     {"cost_usd": 0.01}, "2026-10-01T10:00:01+00:00", ticket_id="ticket-001")

    events = await get_run_events(db_path, run_id)
    assert events is not None
    types = [e["type"] for e in events]
    assert "agent_token" not in types
    assert "agent_done" in types


async def test_get_run_events_returns_none_for_unknown_run(db_path: Path) -> None:
    await init_db(db_path)
    result = await get_run_events(db_path, "00000000-0000-0000-0000-000000000000")
    assert result is None


async def test_get_run_events_for_queue_ticket_returns_only_its_events(
    db_path: Path,
) -> None:
    """Per-ticket row linked to envelope returns only its own events."""
    await init_db(db_path)

    # Queue envelope
    envelope_id = await create_run(db_path, "project-1", "queue", mode="queue")

    # Per-ticket rows (like RunRecorder creates them)
    row_001 = await create_run(
        db_path, "project-1", "ticket-001", mode="single", parent_run_id=envelope_id
    )
    row_002 = await create_run(
        db_path, "project-1", "ticket-002", mode="single", parent_run_id=envelope_id
    )

    # Events stored on the envelope (as emetteur does it)
    await save_event(db_path, envelope_id, "agent_started", "codeur",
                     {"round": 1}, "2026-10-01T10:00:01+00:00", ticket_id="ticket-001")
    await save_event(db_path, envelope_id, "agent_done", "codeur",
                     {"cost_usd": 0.01}, "2026-10-01T10:00:02+00:00", ticket_id="ticket-001")
    await save_event(db_path, envelope_id, "agent_started", "codeur",
                     {"round": 1}, "2026-10-01T10:00:03+00:00", ticket_id="ticket-002")
    await save_event(db_path, envelope_id, "agent_done", "codeur",
                     {"cost_usd": 0.02}, "2026-10-01T10:00:04+00:00", ticket_id="ticket-002")

    events_001 = await get_run_events(db_path, row_001)
    events_002 = await get_run_events(db_path, row_002)
    events_env = await get_run_events(db_path, envelope_id)

    assert events_001 is not None
    assert events_002 is not None
    assert events_env is not None

    # ticket-001 row gets only ticket-001 events
    assert len(events_001) == 2
    assert all(e["type"] in ("agent_started", "agent_done") for e in events_001)

    # ticket-002 row gets only ticket-002 events
    assert len(events_002) == 2

    # envelope gets all 4 events
    assert len(events_env) == 4


async def test_list_runs_exposes_parent_run_id(db_path: Path) -> None:
    """list_runs includes parent_run_id so the frontend knows the hierarchy."""
    await init_db(db_path)

    envelope_id = await create_run(db_path, "project-1", "queue", mode="queue")
    per_ticket_id = await create_run(
        db_path, "project-1", "ticket-001", mode="single", parent_run_id=envelope_id
    )

    rows = await list_runs(db_path, "project-1")
    by_id = {r["id"]: r for r in rows}

    assert by_id[per_ticket_id]["parent_run_id"] == envelope_id
    assert by_id[envelope_id]["parent_run_id"] is None


# ---------------------------------------------------------------------------
# HTTP endpoint tests
# ---------------------------------------------------------------------------


async def test_api_get_events_returns_events_in_order(db_path: Path) -> None:
    await init_db(db_path)
    run_id = await create_run(db_path, "project-1", "ticket-001")
    await save_event(db_path, run_id, "agent_started", "codeur",
                     {"round": 1}, "2026-10-01T10:00:01+00:00")
    await save_event(db_path, run_id, "agent_done", None,
                     {"cost_usd": 0.0}, "2026-10-01T10:00:02+00:00")
    # Un run resté ouvert reçoit au démarrage de l'app un `error`
    # « interrupted » (backend redémarré) : on relit un run terminé.
    await finish_run(db_path, run_id, rounds=1, approved=True, final_status="done")

    with TestClient(app) as client:
        resp = client.get(f"/api/v1/runs/{run_id}/events")

    assert resp.status_code == 200
    events = resp.json()
    assert len(events) == 2
    assert events[0]["type"] == "agent_started"
    assert events[1]["type"] == "agent_done"


async def test_api_get_events_excludes_agent_token(db_path: Path) -> None:
    await init_db(db_path)
    run_id = await create_run(db_path, "project-1", "ticket-001")
    await save_event(db_path, run_id, "agent_token", "codeur",
                     {"token": "tok"}, "2026-10-01T10:00:00+00:00")
    await save_event(db_path, run_id, "agent_done", "codeur",
                     {}, "2026-10-01T10:00:01+00:00")

    with TestClient(app) as client:
        resp = client.get(f"/api/v1/runs/{run_id}/events")

    assert resp.status_code == 200
    types = [e["type"] for e in resp.json()]
    assert "agent_token" not in types
    assert "agent_done" in types


async def test_api_get_events_404_on_unknown_run(db_path: Path) -> None:
    await init_db(db_path)

    with TestClient(app) as client:
        resp = client.get("/api/v1/runs/no-such-run/events")

    assert resp.status_code == 404


async def test_api_queue_ticket_row_returns_its_own_events(db_path: Path) -> None:
    """The per-ticket row id (from list_runs) lets the caller fetch that ticket's events."""
    await init_db(db_path)

    envelope_id = await create_run(db_path, "project-1", "queue", mode="queue")
    row_001 = await create_run(
        db_path, "project-1", "ticket-001", mode="single", parent_run_id=envelope_id
    )

    await save_event(db_path, envelope_id, "agent_started", "codeur",
                     {}, "2026-10-01T10:00:01+00:00", ticket_id="ticket-001")
    await save_event(db_path, envelope_id, "agent_done", "codeur",
                     {}, "2026-10-01T10:00:02+00:00", ticket_id="ticket-001")

    with TestClient(app) as client:
        # Simulate what the frontend does: get the run id from list_runs, then fetch events
        runs_resp = client.get("/api/v1/projects/project-1/runs")
        assert runs_resp.status_code == 200

        events_resp = client.get(f"/api/v1/runs/{row_001}/events")

    assert events_resp.status_code == 200
    events = events_resp.json()
    assert len(events) == 2
    assert all(e["type"] in ("agent_started", "agent_done") for e in events)


# ---------------------------------------------------------------------------
# run_closed carries db_run_id
# ---------------------------------------------------------------------------


async def test_run_closed_carries_db_run_id(db_path: Path) -> None:
    """run_closed event's data includes db_run_id for the events endpoint."""
    from unittest.mock import AsyncMock, MagicMock

    from tessera.services.event_hub import EventHub
    from tessera.services.pipeline_events import EventType, OrchestratorEvent
    from tessera.services.run_executor import emetteur, _clore
    from tessera.services.run_registry import RunActif

    await init_db(db_path)

    published: list[OrchestratorEvent] = []

    hub = MagicMock(spec=EventHub)
    hub.publish = AsyncMock(side_effect=lambda e: published.append(e))

    run = RunActif(
        run_id="ws-run-id",
        project_id="project-1",
        ticket_id="ticket-001",
        mode="single",
    )
    run_id_en_base = await create_run(db_path, "project-1", "ticket-001")

    envoyer = emetteur(hub, run, run_id_en_base)
    await _clore(run, run_id_en_base, [], None, envoyer)

    run_closed = next(e for e in published if e.type == EventType.RUN_CLOSED)
    assert run_closed.data["db_run_id"] == run_id_en_base
