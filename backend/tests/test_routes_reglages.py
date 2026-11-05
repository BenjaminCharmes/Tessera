"""Routes GET/PUT/DELETE /api/v1/reglages and the stricter Origin check (ticket-808)."""
import asyncio
import logging
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera import reglages
from tessera.config import settings
from tessera.main import app
from tessera.services.noyau.database import init_db
from tessera.services.pipeline.run_registry import RUN_REGISTRY

_URL = "/api/v1/reglages"
_VITE = {"Origin": "http://localhost:5173"}


@pytest.fixture(autouse=True)
def _etat_propre(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    db_path = tmp_path / "tessera.db"
    asyncio.run(init_db(db_path))
    monkeypatch.setattr(settings, "ide_db_path", db_path)
    monkeypatch.setattr(settings, "static_token", "")
    monkeypatch.setattr(settings, "allowed_hosts", "")
    monkeypatch.setattr(settings, "allowed_origins", "")
    reglages._SURCHARGES.clear()
    yield
    reglages._SURCHARGES.clear()
    for run_id in [r["run_id"] for r in RUN_REGISTRY.instantane()]:
        RUN_REGISTRY.fermer(run_id)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, base_url="http://localhost")


def _ligne(client: TestClient, nom: str) -> dict[str, object]:
    return next(r for r in client.get(_URL).json() if r["nom"] == nom)


def test_get_lists_the_five_settings_with_default_bounds_and_effect(
    client: TestClient,
) -> None:
    lignes = client.get(_URL).json()
    assert {r["nom"] for r in lignes} == set(reglages.REGISTRE)
    run = _ligne(client, "run_max_budget_usd")
    assert run["minimum"] == 0.5 and run["maximum"] == 50.0
    assert run["effet"] == "prochain_run" and run["modifie"] is False
    assert run["defaut"] == run["valeur"] == settings.run_max_budget_usd
    assert _ligne(client, "max_parallel_test_runs")["effet"] == "machine"


def test_put_with_a_declared_origin_changes_the_value(client: TestClient) -> None:
    rep = client.put(f"{_URL}/run_max_budget_usd", json={"valeur": 7.5}, headers=_VITE)
    assert rep.status_code == 200
    assert rep.json()["valeur"] == 7.5 and rep.json()["modifie"] is True
    assert _ligne(client, "run_max_budget_usd")["valeur"] == 7.5


def test_put_without_origin_is_forbidden(client: TestClient) -> None:
    rep = client.put(f"{_URL}/run_max_budget_usd", json={"valeur": 7.5})
    assert rep.status_code == 403
    assert _ligne(client, "run_max_budget_usd")["modifie"] is False


def test_put_from_a_loopback_port_that_is_not_declared_is_forbidden(
    client: TestClient,
) -> None:
    rep = client.put(
        f"{_URL}/run_max_budget_usd",
        json={"valeur": 7.5},
        headers={"Origin": "http://localhost:9999"},
    )
    assert rep.status_code == 403


def test_put_from_the_tauri_origin_is_accepted(client: TestClient) -> None:
    rep = client.put(
        f"{_URL}/run_max_budget_usd",
        json={"valeur": 7.5},
        headers={"Origin": "tauri://localhost"},
    )
    assert rep.status_code == 200


def test_put_from_an_origin_added_by_allowed_origins_is_accepted(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "allowed_origins", "http://localhost:9999")
    rep = client.put(
        f"{_URL}/run_max_budget_usd",
        json={"valeur": 7.5},
        headers={"Origin": "http://localhost:9999"},
    )
    assert rep.status_code == 200


def test_delete_returns_the_setting_to_its_default(client: TestClient) -> None:
    client.put(f"{_URL}/run_max_budget_usd", json={"valeur": 7.5}, headers=_VITE)
    rep = client.delete(f"{_URL}/run_max_budget_usd", headers=_VITE)
    assert rep.status_code == 200
    assert rep.json()["modifie"] is False
    assert rep.json()["valeur"] == settings.run_max_budget_usd


def test_delete_without_origin_is_forbidden(client: TestClient) -> None:
    assert client.delete(f"{_URL}/run_max_budget_usd").status_code == 403


def test_put_out_of_bounds_is_422_and_zero_for_a_budget_is_422(
    client: TestClient,
) -> None:
    for valeur in (51, 0.1, 0):
        rep = client.put(
            f"{_URL}/run_max_budget_usd", json={"valeur": valeur}, headers=_VITE
        )
        assert rep.status_code == 422, valeur
    rep = client.put(
        f"{_URL}/max_parallel_test_runs", json={"valeur": "deux"}, headers=_VITE
    )
    assert rep.status_code == 422


def test_put_a_secret_name_is_404_and_the_message_does_not_name_it(
    client: TestClient,
) -> None:
    for nom in ("static_token", "anthropic_api_key"):
        rep = client.put(f"{_URL}/{nom}", json={"valeur": "x"}, headers=_VITE)
        assert rep.status_code == 404
        assert nom not in rep.text
    assert client.delete(f"{_URL}/static_token", headers=_VITE).status_code == 404


def test_get_without_origin_still_works(client: TestClient) -> None:
    assert client.get(_URL).status_code == 200


def test_static_token_is_still_required_when_set(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "static_token", "jeton-de-test")
    corps = {"valeur": 7.5}
    assert client.put(f"{_URL}/run_max_budget_usd", json=corps, headers=_VITE).status_code == 401
    ok = client.put(
        f"{_URL}/run_max_budget_usd",
        json=corps,
        headers={**_VITE, "Authorization": "Bearer jeton-de-test"},
    )
    assert ok.status_code == 200


def test_runs_ouverts_counts_the_open_runs(client: TestClient) -> None:
    RUN_REGISTRY.ouvrir("projet-un")
    RUN_REGISTRY.ouvrir("projet-deux")
    rep = client.put(f"{_URL}/run_max_budget_usd", json={"valeur": 7.5}, headers=_VITE)
    assert rep.json()["runs_ouverts"] == 2
    # Un réglage de machine ne se fige pas par run.
    assert _ligne(client, "max_parallel_test_runs")["runs_ouverts"] == 0
    assert _ligne(client, "dialogue_timeout_s")["runs_ouverts"] == 0


def test_put_logs_the_name_and_both_values(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO):
        client.put(f"{_URL}/run_max_budget_usd", json={"valeur": 7.5}, headers=_VITE)
    rec = next(r for r in caplog.records if r.getMessage() == "reglage_modifie")
    assert getattr(rec, "nom") == "run_max_budget_usd"
    assert getattr(rec, "ancienne") == settings.run_max_budget_usd
    assert getattr(rec, "nouvelle") == 7.5


def test_other_routes_keep_accepting_a_request_without_origin(
    client: TestClient,
) -> None:
    assert client.get("/api/v1/projects").status_code == 200
    assert client.post("/api/v1/orchestrator/answer", json={}).status_code != 403
