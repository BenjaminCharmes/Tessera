"""Pipeline settings from the UI — ticket-196.

Testeur, sécurité, validateur, autonomie et `merge_without_ci` n'étaient
modifiables qu'en ouvrant `agents.json` ; seul le modèle d'un agent l'était.
"""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.services.run_registry import RUN_REGISTRY

_MANIFESTE = {
    "project_id": "mon-projet",
    "artifacts": "tracked",
    "git_root": "ancestor",
    "services": [{"nom": "dev", "commande": "npm run dev"}],
    "agents": [{"role": "codeur", "model": "claude-sonnet-4-6", "max_tokens": 8192,
                "prompt_file": "agents/prompts/codeur.md", "active": True}],
    "pipeline": {"max_review_rounds": 3, "securite_enabled": True},
    "autonomy": "pr",
}


@pytest.fixture(autouse=True)
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ws = tmp_path / "workspace"
    projet = ws / "mon-projet"
    projet.mkdir(parents=True)
    (projet / "CLAUDE.md").write_text("# mon-projet\n", encoding="utf-8")
    (projet / "agents.json").write_text(json.dumps(_MANIFESTE), encoding="utf-8")
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    return ws


def _manifeste(ws: Path) -> dict[str, object]:
    return json.loads((ws / "mon-projet" / "agents.json").read_text(encoding="utf-8"))


def test_get_rend_la_configuration_effective_defauts_compris() -> None:
    body = TestClient(app).get("/api/v1/projects/mon-projet/pipeline").json()
    assert body == {
        "max_review_rounds": 3, "testeur_enabled": False, "test_command": None,
        "securite_enabled": True, "validateur_enabled": False,
        "autonomy": "pr", "merge_without_ci": False,
    }


def test_le_patch_preserve_le_reste_du_manifeste(workspace: Path) -> None:
    resp = TestClient(app).patch(
        "/api/v1/projects/mon-projet/pipeline",
        json={"validateur_enabled": True, "autonomy": "merge", "merge_without_ci": True},
    )
    assert resp.status_code == 200
    assert resp.json()["validateur_enabled"] is True
    assert resp.json()["autonomy"] == "merge"
    m = _manifeste(workspace)
    assert m["services"] == _MANIFESTE["services"]
    assert m["artifacts"] == "tracked"
    assert m["git_root"] == "ancestor"
    assert m["agents"] == _MANIFESTE["agents"]
    assert m["pipeline"]["securite_enabled"] is True, "un champ non reçu ne bouge pas"
    assert m["merge_without_ci"] is True


def test_le_testeur_sans_commande_est_refuse(workspace: Path) -> None:
    resp = TestClient(app).patch(
        "/api/v1/projects/mon-projet/pipeline", json={"testeur_enabled": True}
    )
    assert resp.status_code == 400
    assert "test_command" in resp.json()["detail"]
    assert "testeur_enabled" not in _manifeste(workspace)["pipeline"]


def test_le_testeur_avec_commande_passe() -> None:
    resp = TestClient(app).patch(
        "/api/v1/projects/mon-projet/pipeline",
        json={"testeur_enabled": True, "test_command": "npm run test -- --run"},
    )
    assert resp.status_code == 200
    assert resp.json()["test_command"] == "npm run test -- --run"


def test_une_autonomie_inconnue_est_refusee(workspace: Path) -> None:
    resp = TestClient(app).patch(
        "/api/v1/projects/mon-projet/pipeline", json={"autonomy": "yolo"}
    )
    assert resp.status_code == 400
    assert _manifeste(workspace)["autonomy"] == "pr"


def test_refuse_pendant_un_run(workspace: Path) -> None:
    # La politique se lit une fois avant le premier agent (ADR-027) : un
    # changement ne vaudrait qu'au run suivant, et l'écran doit le dire.
    run = RUN_REGISTRY.ouvrir("mon-projet", ticket_id="ticket-001")
    try:
        resp = TestClient(app).patch(
            "/api/v1/projects/mon-projet/pipeline", json={"securite_enabled": False}
        )
    finally:
        RUN_REGISTRY.fermer(run.run_id)
    assert resp.status_code == 409
    assert _manifeste(workspace)["pipeline"]["securite_enabled"] is True
