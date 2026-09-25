"""Un projet en `git_root: ancestor` n'est pas un projet sans depot — ticket-171.

Le panneau Git d'`ide-core` annoncait « ce projet n'est pas versionne » et
proposait d'initialiser un depot — qui aurait ete imbrique dans celui de
Tessera, ce qu'ADR-024 existe pour empecher.
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app


@pytest.fixture(autouse=True)
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ws = tmp_path / "workspace"
    (ws / "bootstrap").mkdir(parents=True)
    (ws / "bootstrap" / "CLAUDE.md").write_text("# bootstrap\n", encoding="utf-8")
    (ws / "ordinaire").mkdir(parents=True)
    (ws / "ordinaire" / "CLAUDE.md").write_text("# ordinaire\n", encoding="utf-8")
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    monkeypatch.setattr(settings, "github_token", "")
    return ws


def _declare(projet: Path, **champs: object) -> None:
    (projet / "agents.json").write_text(json.dumps(champs), encoding="utf-8")


def test_le_projet_qui_declare_ancestor_le_dit(workspace: Path) -> None:
    _declare(workspace / "bootstrap", git_root="ancestor")

    corps = TestClient(app).get("/api/v1/projects/bootstrap/git/status").json()

    assert corps["uses_parent_repository"] is True


def test_un_projet_ordinaire_ne_le_dit_pas(workspace: Path) -> None:
    _declare(workspace / "ordinaire", autonomy="pr")

    corps = TestClient(app).get("/api/v1/projects/ordinaire/git/status").json()

    assert corps["uses_parent_repository"] is False


def test_sans_manifeste_le_projet_ne_le_dit_pas(workspace: Path) -> None:
    corps = TestClient(app).get("/api/v1/projects/ordinaire/git/status").json()

    assert corps["uses_parent_repository"] is False


def test_initialiser_est_refuse_sur_un_projet_en_ancestor(workspace: Path) -> None:
    """Le bouton disparait de l'ecran ; l'endpoint reste appelable (ADR-027)."""
    _declare(workspace / "bootstrap", git_root="ancestor")

    resp = TestClient(app).post("/api/v1/projects/bootstrap/git/init")

    assert resp.status_code == 422
    assert "git_root" in resp.json()["detail"]


def test_initialiser_reste_permis_sur_un_projet_ordinaire(workspace: Path) -> None:
    _declare(workspace / "ordinaire", autonomy="pr")

    resp = TestClient(app).post("/api/v1/projects/ordinaire/git/init")

    assert resp.status_code == 200
    assert resp.json()["is_repository"] is True
