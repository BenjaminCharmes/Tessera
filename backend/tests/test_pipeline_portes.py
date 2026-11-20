"""A pipeline gate is not lowered while a run is alive — ticket-880."""
import json
import logging
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.routers.agent_admin import get_registry, router
from tessera.services.agents.agent_registry import AgentRegistryService
from tessera.services.gardes.portes_pipeline import abaisse_une_porte
from tessera.services.pipeline.run_registry import RUN_REGISTRY

_ACTUEL: dict[str, object] = {
    "securite_enabled": True,
    "validateur_enabled": True,
    "testeur_enabled": True,
    "autonomy": "pr",
    "merge_without_ci": False,
    "test_command": "pytest -q",
}
_MANIFESTE = {
    "project_id": "mon-projet",
    "agents": [{"role": "codeur", "model": "claude-sonnet-4-6", "max_tokens": 8192,
                "prompt_file": "agents/prompts/codeur.md", "active": True}],
    "pipeline": {"securite_enabled": True},
    "autonomy": "commit",
}
_URL = "/api/v1/projects/mon-projet/pipeline"


@pytest.mark.parametrize(
    ("demande", "attendu"),
    [
        ({"securite_enabled": False}, ["securite_enabled"]),
        ({"validateur_enabled": False}, ["validateur_enabled"]),
        ({"testeur_enabled": False}, ["testeur_enabled"]),
        ({"autonomy": "merge"}, ["autonomy"]),
        ({"merge_without_ci": True}, ["merge_without_ci"]),
        ({"test_command": "true"}, ["test_command"]),
        ({"test_command": None}, ["test_command"]),
    ],
)
def test_abaisse_une_porte_names_each_lowered_field(
    demande: dict[str, object], attendu: list[str]
) -> None:
    assert abaisse_une_porte(_ACTUEL, demande) == attendu


@pytest.mark.parametrize(
    "demande",
    [
        {"securite_enabled": True},
        {"autonomy": "commit"},
        {"autonomy": "pr"},
        {"merge_without_ci": False},
        {"test_command": " pytest -q "},
        {"max_review_rounds": 5},
        {},
    ],
)
def test_abaisse_une_porte_ignores_raises_and_unchanged_values(
    demande: dict[str, object]
) -> None:
    assert abaisse_une_porte(_ACTUEL, demande) == []
    assert abaisse_une_porte({**_ACTUEL, "autonomy": "merge"}, {"autonomy": "pr"}) == []


def test_abaisse_une_porte_fails_closed_on_unknown_autonomy() -> None:
    assert abaisse_une_porte(_ACTUEL, {"autonomy": "yolo"}) == ["autonomy"]


@pytest.fixture(autouse=True)
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ws = tmp_path / "workspace"
    projet = ws / "mon-projet"
    projet.mkdir(parents=True)
    (projet / "CLAUDE.md").write_text("# mon-projet\n", encoding="utf-8")
    (projet / "agents.json").write_text(json.dumps(_MANIFESTE), encoding="utf-8")
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    return ws


@pytest.fixture()
def run_sur_un_autre_projet() -> Iterator[None]:
    run = RUN_REGISTRY.ouvrir("autre-projet", ticket_id="ticket-001")
    try:
        yield
    finally:
        RUN_REGISTRY.fermer(run.run_id)


@pytest.mark.usefixtures("run_sur_un_autre_projet")
def test_patch_lowering_a_gate_is_refused_while_another_project_runs(workspace: Path) -> None:
    resp = TestClient(app).patch(_URL, json={"securite_enabled": False})
    assert resp.status_code == 409
    manifeste = json.loads((workspace / "mon-projet" / "agents.json").read_text(encoding="utf-8"))
    assert manifeste["pipeline"]["securite_enabled"] is True


@pytest.mark.usefixtures("run_sur_un_autre_projet")
def test_patch_raising_a_gate_is_accepted_while_a_run_is_alive() -> None:
    resp = TestClient(app).patch(_URL, json={"securite_enabled": True})
    assert resp.status_code == 200


def test_patch_lowering_is_accepted_and_logged_without_a_run(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        resp = TestClient(app).patch(_URL, json={"autonomy": "merge"})
    assert resp.status_code == 200
    assert resp.json()["autonomy"] == "merge"
    enregistrements = [r for r in caplog.records if r.getMessage() == "porte_abaissee"]
    assert len(enregistrements) == 1
    champs_journalises = vars(enregistrements[0])
    assert champs_journalises["champs"] == ["autonomy"]
    assert champs_journalises["project_id"] == "mon-projet"


def test_put_agent_admin_is_refused_while_a_run_is_alive(tmp_path: Path) -> None:
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "traducteur.md").write_text("Tu traduis.", encoding="utf-8")
    service = AgentRegistryService(prompts)
    admin = FastAPI()
    admin.include_router(router, prefix="/api/v1")
    admin.dependency_overrides[get_registry] = lambda: service
    client = TestClient(admin)
    base = "/api/v1/agents/registry"
    run = RUN_REGISTRY.ouvrir("mon-projet", ticket_id="ticket-001")
    try:
        put = client.put(f"{base}/traducteur", json={"system_prompt": "Autre."})
        post = client.post(base, json={"role": "nouveau", "system_prompt": "Texte."})
        delete = client.delete(f"{base}/traducteur")
    finally:
        RUN_REGISTRY.fermer(run.run_id)
    assert (put.status_code, post.status_code, delete.status_code) == (409, 409, 409)
    assert (prompts / "traducteur.md").read_text(encoding="utf-8") == "Tu traduis."
    assert client.put(f"{base}/traducteur", json={"system_prompt": "Autre."}).status_code == 200
