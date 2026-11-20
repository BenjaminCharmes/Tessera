"""Doors next to the role prompts, closed during a run — ticket-881."""
import json
import logging
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.services.pipeline.run_registry import RUN_REGISTRY

_AGENTS = {
    "project_id": "mon-projet",
    "agents": [
        {"role": "securite", "model": "claude-sonnet-4-6", "max_tokens": 4096,
         "prompt_file": "agents/prompts/securite.md", "active": True},
    ],
}


@pytest.fixture(autouse=True)
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ws = tmp_path / "workspace"
    for nom in ("mon-projet", "autre-projet"):
        projet = ws / nom
        projet.mkdir(parents=True)
        (projet / "CLAUDE.md").write_text(f"# {nom}\n", encoding="utf-8")
    (ws / "mon-projet" / "agents.json").write_text(json.dumps(_AGENTS), encoding="utf-8")
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    return ws


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def run_vivant() -> Iterator[None]:
    """A live run on another project than the one the request targets."""
    run = RUN_REGISTRY.ouvrir("autre-projet", "ticket-001", mode="single")
    yield
    RUN_REGISTRY.fermer(run.run_id)


def _modele_ecrit(workspace: Path) -> str:
    ecrit = json.loads((workspace / "mon-projet" / "agents.json").read_text(encoding="utf-8"))
    return str(ecrit["agents"][0]["model"])


def test_put_agent_model_is_refused_while_a_run_lives_elsewhere(
    client: TestClient, workspace: Path, run_vivant: None
) -> None:
    resp = client.put(
        "/api/v1/projects/mon-projet/agents/securite", json={"model": "claude-haiku-4-5"}
    )

    assert resp.status_code == 409
    assert _modele_ecrit(workspace) == "claude-sonnet-4-6"


def test_delete_project_is_refused_while_a_run_lives(
    client: TestClient, workspace: Path, run_vivant: None
) -> None:
    resp = client.delete("/api/v1/projects/mon-projet", params={"confirmed": "true"})

    assert resp.status_code == 409
    assert (workspace / "mon-projet").is_dir()


def test_detach_project_is_refused_while_a_run_lives(
    client: TestClient, workspace: Path, run_vivant: None
) -> None:
    resp = client.post("/api/v1/projects/mon-projet/detach")

    assert resp.status_code == 409
    assert (workspace / "mon-projet").is_dir()


def test_put_agent_model_without_run_succeeds_and_logs_lowered_door(
    client: TestClient, workspace: Path, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING):
        resp = client.put(
            "/api/v1/projects/mon-projet/agents/securite", json={"model": "claude-haiku-4-5"}
        )

    assert resp.status_code == 200
    assert _modele_ecrit(workspace) == "claude-haiku-4-5"
    lignes = [r for r in caplog.records if r.getMessage() == "porte_abaissee"]
    assert len(lignes) == 1
    champs = lignes[0].__dict__
    assert champs["project_id"] == "mon-projet"
    assert champs["role"] == "securite"
    assert champs["model"] == "claude-haiku-4-5"


def test_refused_put_agent_model_logs_nothing(
    client: TestClient, run_vivant: None, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING):
        client.put(
            "/api/v1/projects/mon-projet/agents/securite", json={"model": "claude-haiku-4-5"}
        )

    assert not [r for r in caplog.records if r.getMessage() == "porte_abaissee"]
