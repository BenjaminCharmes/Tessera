"""Choisir le modele d'un agent, projet par projet — ticket-080."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app

_AGENTS = {
    "project_id": "mon-projet",
    "agents": [
        {"role": "codeur", "model": "claude-sonnet-4-6", "max_tokens": 8192,
         "prompt_file": "agents/prompts/codeur.md", "active": True},
        {"role": "validateur", "model": "claude-sonnet-4-6", "max_tokens": 4096,
         "prompt_file": "agents/prompts/validateur.md", "active": True},
    ],
}


@pytest.fixture(autouse=True)
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ws = tmp_path / "workspace"
    projet = ws / "mon-projet"
    projet.mkdir(parents=True)
    (projet / "CLAUDE.md").write_text("# mon-projet\n", encoding="utf-8")
    (projet / "agents.json").write_text(json.dumps(_AGENTS), encoding="utf-8")
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    return ws


def _client() -> TestClient:
    return TestClient(app)


def test_on_lit_le_modele_de_chaque_agent_du_projet(workspace: Path) -> None:
    body = _client().get("/api/v1/projects/mon-projet/agents").json()

    par_role = {a["role"]: a["model"] for a in body["agents"]}
    assert par_role == {
        "codeur": "claude-sonnet-4-6",
        "validateur": "claude-sonnet-4-6",
    }


def test_les_modeles_proposes_sont_ceux_que_l_app_sait_tarifer(workspace: Path) -> None:
    # Choisir un modele hors grille fausserait la ventilation des couts, qui
    # est justement ce qui permet de decider ou descendre en gamme.
    body = _client().get("/api/v1/projects/mon-projet/agents").json()

    assert "claude-haiku-4-5" in body["known_models"]
    assert "claude-sonnet-4-6" in body["known_models"]


def test_changer_le_modele_d_un_agent(workspace: Path) -> None:
    resp = _client().put(
        "/api/v1/projects/mon-projet/agents/validateur",
        json={"model": "claude-haiku-4-5"},
    )

    assert resp.status_code == 200
    ecrit = json.loads(
        (workspace / "mon-projet" / "agents.json").read_text(encoding="utf-8")
    )
    par_role = {a["role"]: a["model"] for a in ecrit["agents"]}
    assert par_role["validateur"] == "claude-haiku-4-5"
    assert par_role["codeur"] == "claude-sonnet-4-6", "les autres ne bougent pas"


def test_un_modele_inconnu_est_refuse(workspace: Path) -> None:
    resp = _client().put(
        "/api/v1/projects/mon-projet/agents/validateur",
        json={"model": "gpt-du-voisin"},
    )

    assert resp.status_code == 422


def test_un_agent_absent_du_projet_renvoie_404(workspace: Path) -> None:
    resp = _client().put(
        "/api/v1/projects/mon-projet/agents/fantome",
        json={"model": "claude-haiku-4-5"},
    )

    assert resp.status_code == 404
