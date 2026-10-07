import pytest
from pathlib import Path

import aiosqlite

from tessera.services.database import (
    create_run,
    finish_run,
    get_project_usage,
    init_db,
    list_runs,
    save_agent_call,
    save_event,
    version_du_schema,
)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test.db"


async def test_init_db_creates_tables(db_path: Path) -> None:
    await init_db(db_path)

    async with aiosqlite.connect(str(db_path)) as db:
        async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ) as cursor:
            tables = {row[0] for row in await cursor.fetchall()}

    assert "pipeline_runs" in tables
    assert "agent_events" in tables


async def test_init_db_is_idempotent(db_path: Path) -> None:
    await init_db(db_path)
    await init_db(db_path)  # second call must not raise or drop tables

    async with aiosqlite.connect(str(db_path)) as db:
        async with db.execute("SELECT COUNT(*) FROM pipeline_runs") as cursor:
            row = await cursor.fetchone()
    assert row is not None and row[0] == 0


async def test_save_run_persists(db_path: Path) -> None:
    await init_db(db_path)

    run_id = await create_run(db_path, "project-1", "ticket-001")
    assert run_id  # non-empty UUID string

    await finish_run(db_path, run_id, rounds=2, approved=True, final_status="done")

    runs = await list_runs(db_path, "project-1")
    assert len(runs) == 1
    assert runs[0]["id"] == run_id
    assert runs[0]["ticket_id"] == "ticket-001"
    assert runs[0]["rounds"] == 2
    assert runs[0]["approved"] is True
    assert runs[0]["final_status"] == "done"
    assert runs[0]["finished_at"] is not None


async def test_list_runs_returns_ordered(db_path: Path) -> None:
    await init_db(db_path)

    run1 = await create_run(db_path, "project-1", "ticket-001")
    run2 = await create_run(db_path, "project-1", "ticket-002")
    await finish_run(db_path, run1, rounds=1, approved=True, final_status="done")
    await finish_run(db_path, run2, rounds=1, approved=False, final_status="blocked")

    runs = await list_runs(db_path, "project-1", limit=10)

    assert len(runs) == 2
    # Most recent first — run2 was created after run1
    assert runs[0]["ticket_id"] == "ticket-002"
    assert runs[1]["ticket_id"] == "ticket-001"


async def test_list_runs_filters_by_project(db_path: Path) -> None:
    await init_db(db_path)

    await create_run(db_path, "project-alpha", "ticket-001")
    await create_run(db_path, "project-beta", "ticket-001")

    alpha = await list_runs(db_path, "project-alpha")
    beta = await list_runs(db_path, "project-beta")

    assert len(alpha) == 1
    assert len(beta) == 1


async def test_list_runs_respects_limit(db_path: Path) -> None:
    await init_db(db_path)

    for i in range(5):
        await create_run(db_path, "project-1", f"ticket-{i:03d}")

    runs = await list_runs(db_path, "project-1", limit=3)
    assert len(runs) == 3


async def test_save_event_persists(db_path: Path) -> None:
    await init_db(db_path)

    run_id = await create_run(db_path, "project-1", "ticket-001")
    await save_event(
        db_path,
        run_id,
        event_type="agent_started",
        agent="codeur",
        data={"round": 1},
        timestamp="2026-06-20T12:00:00+00:00",
    )

    async with aiosqlite.connect(str(db_path)) as db:
        async with db.execute(
            "SELECT type, agent, data_json FROM agent_events WHERE run_id=?", (run_id,)
        ) as cursor:
            rows = await cursor.fetchall()

    assert len(rows) == 1
    assert rows[0][0] == "agent_started"
    assert rows[0][1] == "codeur"


async def test_init_db_creates_agent_calls_table(db_path: Path) -> None:
    await init_db(db_path)

    async with aiosqlite.connect(str(db_path)) as db:
        async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ) as cursor:
            tables = {row[0] for row in await cursor.fetchall()}

    assert "agent_calls" in tables


async def test_save_agent_call_persists(db_path: Path) -> None:
    await init_db(db_path)

    run_id = await create_run(db_path, "project-1", "ticket-001")
    await save_agent_call(
        db_path,
        run_id=run_id,
        ticket_id="ticket-001",
        role="codeur",
        model="claude-sonnet-4-6",
        input_tokens=1000,
        output_tokens=500,
        cache_read_tokens=200,
        cost_usd=0.003,
        duration_ms=1500,
    )

    async with aiosqlite.connect(str(db_path)) as db:
        async with db.execute(
            "SELECT role, model, input_tokens, output_tokens, cost_usd FROM agent_calls WHERE run_id=?",
            (run_id,),
        ) as cursor:
            rows = await cursor.fetchall()

    assert len(rows) == 1
    assert rows[0][0] == "codeur"
    assert rows[0][1] == "claude-sonnet-4-6"
    assert rows[0][2] == 1000
    assert rows[0][4] == pytest.approx(0.003)


async def test_list_runs_includes_total_cost(db_path: Path) -> None:
    await init_db(db_path)

    run_id = await create_run(db_path, "project-1", "ticket-001")
    await finish_run(db_path, run_id, rounds=1, approved=True, final_status="done")
    await save_agent_call(
        db_path, run_id, "ticket-001", "codeur", "claude-sonnet-4-6",
        1000, 500, 0, 0.01, 1000,
    )
    await save_agent_call(
        db_path, run_id, "ticket-001", "reviewer", "claude-sonnet-4-6",
        800, 300, 0, 0.005, 800,
    )

    runs = await list_runs(db_path, "project-1")
    assert len(runs) == 1
    assert runs[0]["total_cost_usd"] == pytest.approx(0.015)


async def test_get_project_usage_empty(db_path: Path) -> None:
    await init_db(db_path)
    usage = await get_project_usage(db_path, "project-empty")
    assert usage["total_cost_usd"] == 0.0
    assert usage["total_tokens"] == 0
    assert usage["total_runs"] == 0
    assert usage["per_ticket"] == []


async def test_get_project_usage_aggregates(db_path: Path) -> None:
    await init_db(db_path)

    run_id = await create_run(db_path, "project-1", "ticket-001")
    await save_agent_call(
        db_path, run_id, "ticket-001", "codeur", "claude-sonnet-4-6",
        1000, 500, 200, 0.01, 1000,
    )
    run_id2 = await create_run(db_path, "project-1", "ticket-002")
    await save_agent_call(
        db_path, run_id2, "ticket-002", "codeur", "claude-haiku-4-5",
        2000, 1000, 0, 0.005, 800,
    )

    usage = await get_project_usage(db_path, "project-1")

    assert usage["total_runs"] == 2
    assert usage["total_cost_usd"] == pytest.approx(0.015)
    assert usage["total_tokens"] == 1000 + 500 + 200 + 2000 + 1000
    assert len(usage["per_ticket"]) == 2
    # sorted by cost desc
    assert usage["per_ticket"][0]["ticket_id"] == "ticket-001"
    assert usage["per_ticket"][0]["total_cost_usd"] == pytest.approx(0.01)


async def test_list_runs_departage_a_egalite_d_horodatage(db_path: Path) -> None:
    # Instabilite vecue : deux runs crees dans la meme milliseconde ont le meme
    # `started_at`, et SQLite tranchait seul. La suite echouait une fois sur
    # quelques dizaines, sur un test qui n'avait pas change.
    await init_db(db_path)

    ids = [await create_run(db_path, "project-1", f"ticket-{i:03d}") for i in range(6)]

    runs = await list_runs(db_path, "project-1", limit=10)

    assert [r["id"] for r in runs] == list(reversed(ids))


# ---------------------------------------------------------------------------
# Mode column — ticket-263
# ---------------------------------------------------------------------------


async def test_migration_adds_mode_column(db_path: Path) -> None:
    """The mode column exists after init_db and init_db is idempotent."""
    await init_db(db_path)
    await init_db(db_path)  # second call must not raise

    async with aiosqlite.connect(str(db_path)) as db:
        async with db.execute("PRAGMA table_info(pipeline_runs)") as cursor:
            columns = {row[1] for row in await cursor.fetchall()}

    assert "mode" in columns
    assert version_du_schema() == 7


async def test_create_run_stores_mode(db_path: Path) -> None:
    """create_run persists the mode passed by the caller."""
    await init_db(db_path)

    run_id = await create_run(db_path, "project-1", "queue", mode="queue")

    async with aiosqlite.connect(str(db_path)) as db:
        async with db.execute(
            "SELECT mode FROM pipeline_runs WHERE id = ?", (run_id,)
        ) as cursor:
            row = await cursor.fetchone()

    assert row is not None
    assert row[0] == "queue"


async def test_create_run_defaults_to_single(db_path: Path) -> None:
    """create_run writes mode='single' when no mode is given."""
    await init_db(db_path)

    run_id = await create_run(db_path, "project-1", "ticket-001")

    async with aiosqlite.connect(str(db_path)) as db:
        async with db.execute(
            "SELECT mode FROM pipeline_runs WHERE id = ?", (run_id,)
        ) as cursor:
            row = await cursor.fetchone()

    assert row is not None
    assert row[0] == "single"


async def test_migration_backfills_queue_and_autonomous_rows(db_path: Path) -> None:
    """Old envelope rows whose ticket_id is 'queue'/'autonomous' get their mode set."""
    # Simulate a pre-migration database: create without mode column.
    async with aiosqlite.connect(str(db_path)) as db:
        await db.execute(
            "CREATE TABLE pipeline_runs (id TEXT PRIMARY KEY, project_id TEXT NOT NULL,"
            " ticket_id TEXT NOT NULL, started_at TEXT NOT NULL,"
            " finished_at TEXT, rounds INTEGER, approved INTEGER, final_status TEXT)"
        )
        await db.execute(
            "INSERT INTO pipeline_runs (id, project_id, ticket_id, started_at)"
            " VALUES ('r-queue', 'p1', 'queue', '2026-01-01T00:00:00+00:00')"
        )
        await db.execute(
            "INSERT INTO pipeline_runs (id, project_id, ticket_id, started_at)"
            " VALUES ('r-auto', 'p1', 'autonomous', '2026-01-01T00:00:00+00:00')"
        )
        await db.execute(
            "INSERT INTO pipeline_runs (id, project_id, ticket_id, started_at)"
            " VALUES ('r-single', 'p1', 'ticket-001', '2026-01-01T00:00:00+00:00')"
        )
        await db.commit()

    await init_db(db_path)

    async with aiosqlite.connect(str(db_path)) as db:
        async with db.execute(
            "SELECT id, mode FROM pipeline_runs ORDER BY id"
        ) as cursor:
            rows = {row[0]: row[1] for row in await cursor.fetchall()}

    assert rows["r-queue"] == "queue"
    assert rows["r-auto"] == "autonomous"
    # Un run single sans mode explicite reste NULL (pas de devinage).
    assert rows["r-single"] is None
