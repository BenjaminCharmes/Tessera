"""Online declaration on the projects overview — ticket-472."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.services.online_declaration import OnlineDeclaration, read_online_declaration
from tessera.services.project_overview import clear_overview_cache

_BASE = "/api/v1/projects"


@pytest.fixture(autouse=True)
def _fresh_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    clear_overview_cache()
    ws = tmp_path / "workspace"
    ws.mkdir()
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    return ws


def _project(ws: Path, name: str, manifest: object | None = None) -> Path:
    folder = ws / name
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "CLAUDE.md").write_text(f"# {name}\n\nProjet {name}.\n", encoding="utf-8")
    if manifest is not None:
        (folder / "agents.json").write_text(json.dumps(manifest), encoding="utf-8")
    return folder


def _overview() -> dict[str, dict[str, object]]:
    resp = TestClient(app).get(f"{_BASE}/overview")
    assert resp.status_code == 200
    return {item["id"]: item for item in resp.json()}


def test_online_declared_follows_the_online_block(_fresh_state: Path) -> None:
    _project(
        _fresh_state,
        "avec",
        {"online": {"domain": "Avec.example.com", "resources": ["vercel"]}},
    )
    _project(_fresh_state, "sans")
    _project(_fresh_state, "autre", {"services": []})
    _project(_fresh_state, "vide", {"online": None})

    body = _overview()

    assert body["avec"]["online_declared"] is True
    assert body["sans"]["online_declared"] is False
    assert body["autre"]["online_declared"] is False
    assert body["vide"]["online_declared"] is False


def test_overview_names_the_domain_and_the_stripe_mode(_fresh_state: Path) -> None:
    stripe = {"webhook_path": "/api/stripe", "events": ["checkout.session.completed"]}
    _project(
        _fresh_state,
        "boutique",
        {"online": {"domain": "Boutique.example.com", "resources": ["stripe"], "stripe": stripe}},
    )

    item = _overview()["boutique"]

    assert item["online_domain"] == "boutique.example.com"
    assert item["online_stripe_mode"] == "test"


def test_missing_folder_declares_nothing() -> None:
    assert read_online_declaration(Path("absent")) == OnlineDeclaration()


def test_stripe_mode_live_and_unknown_values(tmp_path: Path) -> None:
    live = _project(tmp_path, "live", {"online": {"domain": "a.example.com", "stripe": {"mode": "live"}}})
    inconnu = _project(tmp_path, "inconnu", {"online": {"domain": "b.example.com", "stripe": {"mode": "LIVE "}}})
    sans = _project(tmp_path, "sans", {"online": {"domain": "c.example.com"}})

    assert read_online_declaration(live).stripe_mode == "live"
    # Le mode réel ne s'implique jamais : une valeur douteuse se lit « test ».
    assert read_online_declaration(inconnu).stripe_mode == "test"
    assert read_online_declaration(sans).stripe_mode is None


def test_unreadable_manifest_declares_nothing(tmp_path: Path) -> None:
    dossier = tmp_path / "casse"
    dossier.mkdir()
    (dossier / "agents.json").write_text("{pas du json", encoding="utf-8")

    assert read_online_declaration(dossier).declared is False


def test_overview_says_which_projects_run_in_a_worktree(_fresh_state: Path) -> None:
    # Ticket-633 : la carte d'un projet à worktree n'offre pas de file.
    _project(_fresh_state, "isole", {"artifacts": "tracked", "worktree": {}})
    _project(_fresh_state, "local", {"worktree": {}})
    _project(_fresh_state, "checkout")

    body = _overview()

    assert body["isole"]["worktree"] is True
    # Des artefacts `local` refusent le worktree : le run reste dans le checkout.
    assert body["local"]["worktree"] is False
    assert body["checkout"]["worktree"] is False
