"""Modifier le prompt d'un agent depuis l'IDE — ticket-079."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app


@pytest.fixture(autouse=True)
def prompts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    dossier = tmp_path / "prompts"
    dossier.mkdir()
    (dossier / "codeur.md").write_text("Tu implémentes.\n", encoding="utf-8")
    monkeypatch.setattr(settings, "ide_prompts_dir", dossier)
    return dossier


def _client() -> TestClient:
    return TestClient(app)


def test_le_prompt_se_modifie_depuis_l_ide(prompts: Path) -> None:
    # Le prompt décide de tout ce que fait un agent. Le régler demandait
    # d'ouvrir un fichier dans VSCode, alors qu'on venait de le lire à l'écran.
    resp = _client().put(
        "/api/v1/agents/registry/codeur",
        json={"system_prompt": "Tu implémentes, et tu écris des tests d'abord."},
    )

    assert resp.status_code == 200
    assert "tests d'abord" in (prompts / "codeur.md").read_text(encoding="utf-8")


def test_un_prompt_vide_est_refuse(prompts: Path) -> None:
    # Un agent sans prompt n'a plus de définition : il ferait n'importe quoi.
    resp = _client().put(
        "/api/v1/agents/registry/codeur", json={"system_prompt": "   "}
    )

    assert resp.status_code == 422
    assert prompts.joinpath("codeur.md").read_text(encoding="utf-8").strip() != ""


def test_modifier_un_agent_inconnu_renvoie_404(prompts: Path) -> None:
    resp = _client().put(
        "/api/v1/agents/registry/fantome", json={"system_prompt": "x"}
    )

    assert resp.status_code == 404


def test_un_nom_invalide_est_refuse(prompts: Path) -> None:
    resp = _client().put(
        "/api/v1/agents/registry/../../etc/passwd", json={"system_prompt": "x"}
    )

    assert resp.status_code in (404, 422)
