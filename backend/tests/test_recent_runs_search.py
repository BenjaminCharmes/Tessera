"""More recent runs, and a search over them — ticket-335."""
import asyncio
from datetime import date
from pathlib import Path

import aiosqlite
import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.services.database import init_db
from tessera.services.usage_stats import recent_runs

TODAY = date(2026, 9, 28)


async def _run(db: Path, run_id: str, project_id: str, ticket_id: str, minute: int,
               mode: str = "single") -> None:
    async with aiosqlite.connect(str(db)) as conn:
        await conn.execute(
            "INSERT INTO pipeline_runs (id, project_id, ticket_id, started_at, mode)"
            " VALUES (?,?,?,?,?)",
            (run_id, project_id, ticket_id, f"2026-09-27T10:{minute:02d}:00+00:00", mode),
        )
        await conn.commit()


@pytest.fixture
async def db(tmp_path: Path) -> Path:
    path = tmp_path / "tessera.db"
    await init_db(path)
    for i in range(30):
        await _run(path, f"r{i:02d}", "alpha" if i % 2 else "beta", f"ticket-{300 + i}", i)
    await _run(path, "file", "alpha", "ticket-317", 59, mode="queue")
    return path


async def test_the_limit_returns_more_than_the_ten_of_the_stats_view(db: Path) -> None:
    runs = await recent_runs(db, 30, None, limit=25, today=TODAY)

    assert len(runs) == 25
    assert runs[0].id == "r29"


async def test_search_matches_a_ticket_id_or_a_project_and_skips_envelopes(db: Path) -> None:
    par_ticket = await recent_runs(db, 30, None, limit=50, recherche="317", today=TODAY)
    par_projet = await recent_runs(db, 30, None, limit=50, recherche="BETA", today=TODAY)

    # La file 317 porte aussi l'id ticket-317 : elle n'est pas un run de ticket.
    assert [r.id for r in par_ticket] == ["r17"]
    assert len(par_projet) == 15
    assert all(r.project_id == "beta" for r in par_projet)


async def test_search_wildcards_are_literal(db: Path) -> None:
    # `_` et `%` sont des jokers de LIKE : tapés dans la recherche, ils ne
    # doivent rien attraper d'autre qu'eux-mêmes.
    assert await recent_runs(db, 30, None, limit=50, recherche="%", today=TODAY) == []
    assert await recent_runs(db, 30, None, limit=50, recherche="_", today=TODAY) == []


def test_endpoint_passes_limit_and_search_and_bounds_the_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "api.db"
    asyncio.run(init_db(path))
    asyncio.run(_run(path, "r1", "alpha", "ticket-001", 1))
    monkeypatch.setattr(settings, "ide_db_path", path)

    with TestClient(app) as client:
        ok = client.get("/api/v1/usage/recent-runs",
                        params={"days": 90, "limit": 50, "q": "001"})
        trop = client.get("/api/v1/usage/recent-runs", params={"days": 30, "limit": 500})

    assert ok.status_code == 200
    assert [r["id"] for r in ok.json()] == ["r1"]
    assert trop.status_code == 422
