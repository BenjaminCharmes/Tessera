"""One cost-by-role aggregate shared by the breakdown and the statistics — ticket-678."""
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.services.database import (
    create_run,
    get_usage_breakdown,
    init_db,
    save_agent_call,
)
from tessera.services.usage_stats import usage_stats


@pytest.fixture
async def base(tmp_path: Path) -> Path:
    path = tmp_path / "tessera.db"
    await init_db(path)
    for projet, ticket, role, cout in (
        ("alpha", "ticket-001", "codeur", 0.60),
        ("alpha", "ticket-001", "reviewer", 0.10),
        ("beta", "ticket-002", "codeur", 0.25),
        ("beta", "ticket-002", "securite", 0.05),
    ):
        run = await create_run(path, projet, ticket)
        await save_agent_call(
            path, run, ticket, role, "sonnet",
            input_tokens=100, output_tokens=50, cache_read_tokens=0,
            cost_usd=cout, duration_ms=500,
        )
    return path


async def _stats_par_role(base: Path, project_id: str | None) -> dict[str, float]:
    stats = await usage_stats(base, 7, project_id, today=date.today())
    return {ligne.key: ligne.cost_usd for ligne in stats.per_agent}


@pytest.mark.parametrize("project_id", [None, "alpha", "beta"])
async def test_per_agent_sum_matches_between_breakdown_and_stats(
    base: Path, project_id: str | None
) -> None:
    ventilation = await get_usage_breakdown(base, project_id)
    attendu = {a["role"]: a["total_cost_usd"] for a in ventilation["per_agent"]}

    assert attendu
    assert await _stats_par_role(base, project_id) == pytest.approx(attendu)


async def test_stats_and_breakdown_agree_on_calls_and_tokens(base: Path) -> None:
    ventilation = await get_usage_breakdown(base, None)
    stats = await usage_stats(base, 7, None, today=date.today())

    par_role = {a["role"]: a for a in ventilation["per_agent"]}
    for ligne in stats.per_agent:
        assert ligne.calls == par_role[ligne.key]["call_count"]
        assert ligne.tokens == par_role[ligne.key]["total_tokens"]


@pytest.fixture
def client(base: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(settings, "ide_db_path", base)
    return TestClient(app)


def test_global_route_serves_the_declared_model(client: TestClient) -> None:
    with client:
        response = client.get("/api/v1/projects/usage/breakdown")

    corps = response.json()
    assert response.status_code == 200
    assert corps["project_id"] is None
    assert corps["total_cost_usd"] == pytest.approx(1.0)
    assert {a["role"] for a in corps["per_agent"]} == {"codeur", "reviewer", "securite"}
    assert {p["project_id"] for p in corps["per_project"]} == {"alpha", "beta"}
    assert {m["model"] for m in corps["per_model"]} == {"sonnet"}


def test_project_route_keeps_the_existing_fields(client: TestClient) -> None:
    with client:
        response = client.get("/api/v1/projects/alpha/usage/breakdown")

    corps = response.json()
    assert corps["project_id"] == "alpha"
    assert corps["per_project"] == []
    assert set(corps["per_agent"][0]) == {
        "role", "total_cost_usd", "total_tokens", "call_count",
    }


def test_openapi_describes_both_breakdown_routes(client: TestClient) -> None:
    with client:
        paths = client.get("/openapi.json").json()["paths"]

    for chemin in (
        "/api/v1/projects/usage/breakdown",
        "/api/v1/projects/{project_id}/usage/breakdown",
    ):
        schema = paths[chemin]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
        assert schema["$ref"].endswith("/UsageBreakdown")
