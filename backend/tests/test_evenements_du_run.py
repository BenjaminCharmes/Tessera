"""A finished run's events are readable through the API — ticket-280.

Five acceptance criteria:
1. GET /api/v1/runs/{id}/events returns events in ts order.
2. agent_token events are excluded.
3. 404 on an unknown run_id.
4. run_closed carries the db_run_id field.
5. A per-ticket row inside a queue (as returned by list_runs) gives access to
   its own events through that same endpoint.
"""
import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.models.ticket import TicketStatus
from tessera.services.database import (
    create_run,
    get_run_events,
    init_db,
    save_event,
    list_runs,
)
from tessera.services.event_hub import EventHub
from tessera.services.pipeline_events import EventType, PipelineResult
from tessera.services.run_executor import _clore, emetteur
from tessera.services.run_registry import RunActif


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture
async def db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Initialised async database — for pure-async tests."""
    db_path = tmp_path / "tessera.db"
    await init_db(db_path)
    monkeypatch.setattr(settings, "ide_db_path", db_path)
    return db_path


@pytest.fixture
def db_sync(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Initialised database for sync (TestClient) tests."""
    db_path = tmp_path / "tessera.db"
    asyncio.run(init_db(db_path))
    monkeypatch.setattr(settings, "ide_db_path", db_path)
    return db_path


# ------------------------------------------------------------------
# 1 — events are returned in ts order
# ------------------------------------------------------------------

async def test_events_are_returned_in_emission_order(db: Path) -> None:
    run_id = await create_run(db, "p", "ticket-001")
    await save_event(db, run_id, "agent_started", "codeur", {"round": 1},
                     "2026-09-26T08:00:00+00:00")
    await save_event(db, run_id, "agent_done", "codeur", {"cost_usd": 0.01},
                     "2026-09-26T08:01:00+00:00")
    await save_event(db, run_id, "pipeline_done", None, {"approved": True},
                     "2026-09-26T08:02:00+00:00")

    events = await get_run_events(db, run_id)

    assert events is not None
    assert [e["type"] for e in events] == ["agent_started", "agent_done", "pipeline_done"]


# ------------------------------------------------------------------
# 2 — agent_token events are excluded
# ------------------------------------------------------------------

async def test_agent_token_events_are_excluded(db: Path) -> None:
    run_id = await create_run(db, "p", "ticket-001")
    await save_event(db, run_id, "agent_token", "codeur", {"token": "x"},
                     "2026-09-26T08:00:00+00:00")
    await save_event(db, run_id, "agent_done", "codeur", {"cost_usd": 0.01},
                     "2026-09-26T08:01:00+00:00")

    events = await get_run_events(db, run_id)

    assert events is not None
    assert len(events) == 1
    assert events[0]["type"] == "agent_done"


# ------------------------------------------------------------------
# 3 — 404 on unknown run_id
# ------------------------------------------------------------------

async def test_unknown_run_id_returns_none_from_db(db: Path) -> None:
    result = await get_run_events(db, "run-inconnu")
    assert result is None


def test_unknown_run_id_returns_404_via_http(db_sync: Path) -> None:
    with TestClient(app) as client:
        resp = client.get("/api/v1/runs/run-inconnu/events")
    assert resp.status_code == 404


# ------------------------------------------------------------------
# 4 — run_closed carries db_run_id
# ------------------------------------------------------------------

async def test_run_closed_event_carries_db_run_id(db: Path) -> None:
    """_clore puts the database run id in the run_closed event data."""
    run_id_en_base = await create_run(db, "p", "ticket-001")
    hub = EventHub()
    sub = hub.subscribe()
    run = RunActif(run_id="run-ws-1", project_id="p", ticket_id="ticket-001")
    envoyer = emetteur(hub, run, run_id_en_base)

    resultat = PipelineResult(
        ticket_id="ticket-001",
        approved=True,
        rounds=1,
        final_status=TicketStatus.done,
        branch="ticket-001-slug",
        commit_sha="abc1234",
    )
    await _clore(run, run_id_en_base, [resultat], None, envoyer)

    received = sub.vider()
    run_closed = next((e for e in received if e.type is EventType.RUN_CLOSED), None)
    assert run_closed is not None
    assert run_closed.data["db_run_id"] == run_id_en_base


# ------------------------------------------------------------------
# 5 — per-ticket queue row exposes its own events
# ------------------------------------------------------------------

async def test_queue_ticket_events_accessible_via_per_ticket_run_id(db: Path) -> None:
    """list_runs returns the per-ticket run id; get_run_events returns its events.

    In a queue, events are stored on the envelope run. get_run_events detects
    the parent_run_id link and filters by ticket_id, so each per-ticket row
    only surfaces its own events.
    """
    envelope_id = await create_run(db, "p", "queue", mode="queue")
    ticket_run_id = await create_run(
        db, "p", "ticket-001", mode="single", parent_run_id=envelope_id
    )
    # Events under the envelope, tagged by ticket_id
    await save_event(
        db, envelope_id, "agent_started", "codeur", {"stage": "production"},
        "2026-09-26T08:00:00+00:00", ticket_id="ticket-001",
    )
    await save_event(
        db, envelope_id, "pipeline_done", None, {"approved": True},
        "2026-09-26T08:01:00+00:00", ticket_id="ticket-001",
    )
    # Another ticket's events — must not appear in ticket-001's response
    await save_event(
        db, envelope_id, "agent_started", "codeur", {"stage": "production"},
        "2026-09-26T08:02:00+00:00", ticket_id="ticket-002",
    )

    events = await get_run_events(db, ticket_run_id)

    assert events is not None
    assert len(events) == 2
    assert [e["type"] for e in events] == ["agent_started", "pipeline_done"]


def test_queue_ticket_run_id_from_list_runs_is_queryable_via_http(
    db_sync: Path,
) -> None:
    """The id returned by list_runs for a per-ticket row works in the HTTP endpoint."""
    envelope_id = asyncio.run(create_run(db_sync, "p", "queue", mode="queue"))
    ticket_run_id = asyncio.run(
        create_run(db_sync, "p", "ticket-001", mode="single", parent_run_id=envelope_id)
    )
    asyncio.run(
        save_event(
            db_sync, envelope_id, "pipeline_done", None, {"approved": True},
            "2026-09-26T08:00:00+00:00", ticket_id="ticket-001",
        )
    )

    # list_runs returns both rows; the per-ticket row has parent_run_id set
    runs = asyncio.run(list_runs(db_sync, "p"))
    per_ticket_row = next(r for r in runs if r["ticket_id"] == "ticket-001")
    assert per_ticket_row["id"] == ticket_run_id
    assert per_ticket_row["parent_run_id"] == envelope_id

    with TestClient(app) as client:
        resp = client.get(f"/api/v1/runs/{ticket_run_id}/events")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["type"] == "pipeline_done"
