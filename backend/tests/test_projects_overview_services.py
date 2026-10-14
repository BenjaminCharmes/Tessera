"""Services state on the projects overview — ticket-410."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.services.process_registry import PROCESS_REGISTRY, Service
from tessera.services.project_overview import clear_overview_cache

_BASE = "/api/v1/projects"


class _FakeProcess:
    """Stand-in for an asyncio subprocess: only `returncode` is read."""

    def __init__(self, returncode: int | None) -> None:
        self.returncode = returncode


@pytest.fixture(autouse=True)
def _fresh_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    clear_overview_cache()
    ws = tmp_path / "workspace"
    ws.mkdir()
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    monkeypatch.setattr(PROCESS_REGISTRY, "_services", {})
    return ws


def _project(ws: Path, name: str) -> Path:
    folder = ws / name
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "CLAUDE.md").write_text(f"# {name}\n\nProjet {name}.\n", encoding="utf-8")
    return folder


def _overview() -> dict[str, dict[str, object]]:
    resp = TestClient(app).get(f"{_BASE}/overview")
    assert resp.status_code == 200
    return {item["id"]: item for item in resp.json()}


def _register(
    monkeypatch: pytest.MonkeyPatch, project_id: str, returncode: int | None
) -> _FakeProcess:
    process = _FakeProcess(returncode)
    service = Service(nom="web", project_id=project_id, pid=1, processus=process)
    monkeypatch.setattr(PROCESS_REGISTRY, "_services", {project_id: [service]})
    return process


def test_services_declares_follows_the_manifest(_fresh_state: Path) -> None:
    avec = _project(_fresh_state, "avec")
    (avec / "agents.json").write_text(
        json.dumps({"services": [{"nom": "web", "commande": "npm.cmd run dev"}]}),
        encoding="utf-8",
    )
    _project(_fresh_state, "sans")
    vide = _project(_fresh_state, "vide")
    (vide / "agents.json").write_text(json.dumps({"services": []}), encoding="utf-8")

    body = _overview()

    assert body["avec"]["services_declares"] is True
    assert body["sans"]["services_declares"] is False
    assert body["vide"]["services_declares"] is False


def test_services_en_cours_needs_a_live_service_of_that_project(
    _fresh_state: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _project(_fresh_state, "alpha")
    _project(_fresh_state, "beta")
    assert _overview()["alpha"]["services_en_cours"] is False

    _register(monkeypatch, "alpha", None)
    body = _overview()
    assert body["alpha"]["services_en_cours"] is True
    assert body["beta"]["services_en_cours"] is False

    _register(monkeypatch, "alpha", 1)  # registered but dead
    assert _overview()["alpha"]["services_en_cours"] is False


def test_services_en_cours_is_not_frozen_by_the_cache(
    _fresh_state: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _project(_fresh_state, "alpha")
    process = _register(monkeypatch, "alpha", None)
    assert _overview()["alpha"]["services_en_cours"] is True

    process.returncode = 0  # the service exits; nothing else changes

    assert _overview()["alpha"]["services_en_cours"] is False


def test_project_running_the_ide_offers_no_launch(
    _fresh_state: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ide-core runs the IDE itself: launching it from the IDE makes no sense."""
    ide = _project(_fresh_state, "ide")
    (ide / "agents.json").write_text(
        json.dumps({"services": [{"nom": "backend", "commande": "make dev"}]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "tessera.routers.projects.fait_tourner_l_ide", lambda path: path.name == "ide"
    )

    assert _overview()["ide"]["services_declares"] is False
