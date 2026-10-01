"""Usage statistics over a period — ticket-201."""
from datetime import date
from pathlib import Path

import aiosqlite
import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.services.database import init_db
from tessera.services.usage_stats import usage_stats

TODAY = date(2026, 9, 28)


async def _run(
    db: Path,
    run_id: str,
    project_id: str,
    started_at: str,
    *,
    finished_at: str | None = None,
    approved: bool | None = None,
    status: str | None = None,
    rounds: int | None = None,
    mode: str = "single",
) -> None:
    async with aiosqlite.connect(str(db)) as conn:
        await conn.execute(
            "INSERT INTO pipeline_runs (id, project_id, ticket_id, started_at, finished_at,"
            " rounds, approved, final_status, mode) VALUES (?,?,?,?,?,?,?,?,?)",
            (run_id, project_id, f"ticket-{run_id}", started_at, finished_at, rounds,
             None if approved is None else int(approved), status, mode),
        )
        await conn.commit()


async def _call(
    db: Path,
    run_id: str,
    created_at: str,
    *,
    role: str = "codeur",
    model: str = "sonnet",
    tokens_in: int = 100,
    tokens_out: int = 50,
    cost: float = 0.10,
    duration_ms: int = 1000,
) -> None:
    async with aiosqlite.connect(str(db)) as conn:
        await conn.execute(
            "INSERT INTO agent_calls (run_id, ticket_id, role, model, input_tokens,"
            " output_tokens, cache_read_tokens, cost_usd, duration_ms, created_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (run_id, f"ticket-{run_id}", role, model, tokens_in, tokens_out, 0, cost,
             duration_ms, created_at),
        )
        await conn.commit()


async def _chat(db: Path, project_id: str, ts: str, cost: float) -> None:
    async with aiosqlite.connect(str(db)) as conn:
        await conn.execute(
            "INSERT INTO chat_messages (project_id, conversation_id, role, content, cost_usd, ts)"
            " VALUES (?,?,?,?,?,?)",
            (project_id, "c1", "assistant", "ok", cost, ts),
        )
        await conn.commit()


@pytest.fixture
async def db(tmp_path: Path) -> Path:
    path = tmp_path / "tessera.db"
    await init_db(path)
    await _run(path, "a1", "alpha", "2026-09-27T10:00:00+00:00",
               finished_at="2026-09-27T10:10:00+00:00", approved=True, status="done", rounds=1)
    await _call(path, "a1", "2026-09-27T10:01:00+00:00", role="codeur", cost=0.50,
                duration_ms=4000)
    await _call(path, "a1", "2026-09-27T10:05:00+00:00", role="reviewer", model="haiku",
                cost=0.10, duration_ms=2000)
    await _run(path, "a2", "alpha", "2026-09-28T08:00:00+00:00",
               finished_at="2026-09-28T08:20:00+00:00", approved=False, status="blocked",
               rounds=3)
    await _call(path, "a2", "2026-09-28T08:01:00+00:00", cost=0.20)
    await _run(path, "b1", "beta", "2026-09-20T09:00:00+00:00",
               finished_at="2026-09-20T09:05:00+00:00", approved=True, status="done", rounds=1)
    await _call(path, "b1", "2026-09-20T09:01:00+00:00", cost=0.05)
    # Hors de toute période de 30 jours.
    await _run(path, "old", "alpha", "2026-06-01T09:00:00+00:00",
               finished_at="2026-06-01T09:05:00+00:00", approved=True, status="done", rounds=1)
    await _call(path, "old", "2026-06-01T09:01:00+00:00", cost=9.99)
    await _chat(path, "alpha", "2026-09-26T12:00:00+00:00", 0.07)
    return path


async def test_daily_series_has_one_point_per_day_with_empty_days_at_zero(db: Path) -> None:
    stats = await usage_stats(db, days=30, project_id=None, today=TODAY)

    assert len(stats.daily) == 30
    assert stats.daily[0].day == "2026-08-30"
    assert stats.daily[-1].day == "2026-09-28"
    by_day = {p.day: p for p in stats.daily}
    assert by_day["2026-09-27"].cost_usd == pytest.approx(0.60)
    assert by_day["2026-09-27"].runs == 1
    assert by_day["2026-09-21"].cost_usd == 0.0
    assert by_day["2026-09-21"].input_tokens == 0


async def test_totals_cover_the_period_only(db: Path) -> None:
    stats = await usage_stats(db, days=30, project_id=None, today=TODAY)

    assert stats.totals.runs == 3
    assert stats.totals.calls == 4
    assert stats.totals.input_tokens == 400
    assert stats.totals.output_tokens == 200
    assert stats.totals.pipeline_cost_usd == pytest.approx(0.85)
    assert stats.totals.chat_cost_usd == pytest.approx(0.07)
    assert stats.totals.cost_usd == pytest.approx(0.92)
    assert stats.totals.call_duration_ms == 8000


async def test_a_call_outside_the_period_is_counted_nowhere(db: Path) -> None:
    stats = await usage_stats(db, days=7, project_id=None, today=TODAY)

    assert len(stats.daily) == 7
    assert stats.totals.runs == 2
    assert stats.totals.pipeline_cost_usd == pytest.approx(0.80)
    assert all(r.id != "b1" for r in stats.recent_runs)
    assert {p.key for p in stats.per_project} == {"alpha"}


async def test_project_filter_restricts_every_section(db: Path) -> None:
    stats = await usage_stats(db, days=30, project_id="beta", today=TODAY)

    assert stats.totals.runs == 1
    assert stats.totals.pipeline_cost_usd == pytest.approx(0.05)
    assert stats.totals.chat_cost_usd == 0.0
    assert sum(p.cost_usd for p in stats.daily) == pytest.approx(0.05)
    assert [a.key for a in stats.per_agent] == ["codeur"]
    assert [r.id for r in stats.recent_runs] == ["b1"]
    # Ventiler par projet quand on en regarde un seul n'apprend rien.
    assert stats.per_project == []


async def test_breakdowns_are_sorted_by_cost_with_average_call_duration(db: Path) -> None:
    stats = await usage_stats(db, days=30, project_id=None, today=TODAY)

    assert [a.key for a in stats.per_agent] == ["codeur", "reviewer"]
    codeur = stats.per_agent[0]
    assert codeur.calls == 3
    assert codeur.avg_duration_ms == pytest.approx(2000)
    assert [m.key for m in stats.per_model] == ["sonnet", "haiku"]
    assert [p.key for p in stats.per_project] == ["alpha", "beta"]


async def test_quality_reports_approval_statuses_rounds_and_run_duration(db: Path) -> None:
    stats = await usage_stats(db, days=30, project_id=None, today=TODAY)

    assert stats.quality.finished_runs == 3
    assert stats.quality.approval_rate == pytest.approx(2 / 3)
    assert {s.status: s.count for s in stats.quality.by_status} == {"done": 2, "blocked": 1}
    assert stats.quality.avg_rounds == pytest.approx(5 / 3)
    # 10 min, 20 min, 5 min.
    assert stats.quality.avg_run_duration_ms == pytest.approx(35 / 3 * 60_000, rel=1e-3)


async def test_recent_runs_are_newest_first_with_their_cost(db: Path) -> None:
    stats = await usage_stats(db, days=30, project_id=None, today=TODAY)

    assert [r.id for r in stats.recent_runs] == ["a2", "a1", "b1"]
    a1 = stats.recent_runs[1]
    assert a1.cost_usd == pytest.approx(0.60)
    assert a1.input_tokens == 200
    assert a1.duration_ms == 600_000
    assert a1.project_id == "alpha"


async def test_an_empty_database_returns_zeros_and_no_approval_rate(tmp_path: Path) -> None:
    path = tmp_path / "empty.db"
    await init_db(path)

    stats = await usage_stats(path, days=7, project_id=None, today=TODAY)

    assert len(stats.daily) == 7
    assert stats.totals.runs == 0
    assert stats.totals.cost_usd == 0.0
    assert stats.quality.approval_rate is None
    assert stats.quality.avg_rounds is None
    assert stats.recent_runs == []


async def test_a_run_still_in_progress_has_no_duration_and_no_verdict(tmp_path: Path) -> None:
    path = tmp_path / "live.db"
    await init_db(path)
    await _run(path, "live", "alpha", "2026-09-28T08:00:00+00:00")

    stats = await usage_stats(path, days=7, project_id=None, today=TODAY)

    assert stats.totals.runs == 1
    assert stats.quality.finished_runs == 0
    assert stats.quality.approval_rate is None
    assert stats.recent_runs[0].duration_ms is None


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(settings, "ide_db_path", tmp_path / "api.db")
    return TestClient(app)


def test_endpoint_returns_the_requested_period(client: TestClient) -> None:
    with client:
        response = client.get("/api/v1/usage/stats", params={"days": 30})

    assert response.status_code == 200
    body = response.json()
    assert body["days"] == 30
    assert len(body["daily"]) == 30
    assert body["quality"]["approval_rate"] is None


def test_endpoint_rejects_an_unknown_period(client: TestClient) -> None:
    with client:
        response = client.get("/api/v1/usage/stats", params={"days": 12})

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Queue / autonomous envelope filtering — ticket-263
# ---------------------------------------------------------------------------


async def test_recent_runs_excludes_queue_envelope_but_keeps_ticket_runs(
    tmp_path: Path,
) -> None:
    """A queue envelope row is invisible in recent_runs; its ticket runs are not."""
    path = tmp_path / "queue.db"
    await init_db(path)

    # Envelope run (mode=queue) — created by run_executor for the queue itself.
    await _run(path, "env-q", "alpha", "2026-09-27T10:00:00+00:00",
               finished_at="2026-09-27T10:30:00+00:00", approved=True,
               status="done", rounds=0, mode="queue")
    # Per-ticket runs inside the queue — created by RunRecorder with mode=single.
    await _run(path, "t1", "alpha", "2026-09-27T10:01:00+00:00",
               finished_at="2026-09-27T10:10:00+00:00", approved=True,
               status="done", rounds=1, mode="single")
    await _run(path, "t2", "alpha", "2026-09-27T10:11:00+00:00",
               finished_at="2026-09-27T10:20:00+00:00", approved=True,
               status="done", rounds=1, mode="single")

    stats = await usage_stats(path, days=7, project_id=None, today=TODAY)

    ids = [r.id for r in stats.recent_runs]
    assert "env-q" not in ids
    assert "t1" in ids
    assert "t2" in ids


async def test_totals_run_count_excludes_queue_and_autonomous_rows(
    tmp_path: Path,
) -> None:
    """Run totals count only single-mode rows; envelope rows are invisible."""
    path = tmp_path / "modes.db"
    await init_db(path)

    await _run(path, "s1", "proj", "2026-09-27T10:00:00+00:00",
               finished_at="2026-09-27T10:10:00+00:00",
               approved=True, status="done", rounds=1, mode="single")
    await _run(path, "q1", "proj", "2026-09-27T09:00:00+00:00",
               finished_at="2026-09-27T09:30:00+00:00",
               approved=True, status="done", rounds=0, mode="queue")
    await _run(path, "au1", "proj", "2026-09-27T08:00:00+00:00",
               finished_at="2026-09-27T08:40:00+00:00",
               approved=True, status="done", rounds=0, mode="autonomous")

    stats = await usage_stats(path, days=7, project_id=None, today=TODAY)

    # Only the single-mode run counts.
    assert stats.totals.runs == 1
    assert stats.quality.finished_runs == 1
    ids = [r.id for r in stats.recent_runs]
    assert "q1" not in ids
    assert "au1" not in ids
    assert "s1" in ids


async def test_null_mode_rows_are_treated_as_single(tmp_path: Path) -> None:
    """Legacy rows (mode IS NULL) are counted as single, not excluded."""
    path = tmp_path / "legacy.db"
    await init_db(path)

    # Insert directly with mode=NULL to simulate a pre-migration row.
    async with aiosqlite.connect(str(path)) as conn:
        await conn.execute(
            "INSERT INTO pipeline_runs"
            " (id, project_id, ticket_id, started_at, finished_at, rounds, approved,"
            "  final_status, mode)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            ("legacy-1", "proj", "ticket-old", "2026-09-27T10:00:00+00:00",
             "2026-09-27T10:10:00+00:00", 1, 1, "done", None),
        )
        await conn.commit()

    stats = await usage_stats(path, days=7, project_id=None, today=TODAY)

    assert stats.totals.runs == 1
    assert stats.recent_runs[0].id == "legacy-1"
