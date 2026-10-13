"""Endpoint POST /api/v1/signalements — ticket-407."""
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app


@pytest.fixture(autouse=True)
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ws = tmp_path / "workspace"
    for name in ("ide-core", "mon-projet"):
        (ws / name / "tickets" / "todo").mkdir(parents=True)
        (ws / name / "CLAUDE.md").write_text(f"# {name}\n", encoding="utf-8")
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    return ws


def _payload(**overrides: str) -> dict[str, str]:
    payload = {
        "projet": "mon-projet",
        "nature": "bug",
        "titre": "Le bouton ne répond pas",
        "description": "Rien ne se passe au clic.",
    }
    payload.update(overrides)
    return payload


def _envoyer(**overrides: str) -> httpx.Response:
    return TestClient(app).post("/api/v1/signalements", json=_payload(**overrides))


def _tickets(ws: Path, projet: str) -> list[Path]:
    return sorted((ws / projet / "tickets" / "todo").glob("*.md"))


def test_bug_creates_a_fix_ticket_in_ide_core(workspace: Path) -> None:
    resp = _envoyer(nature="bug")

    assert resp.status_code == 201
    body = resp.json()
    assert body["type"] == "fix"
    assert body["status"] == "todo"
    assert body["priority"] == "medium"
    assert body["agent"] == "codeur"
    assert body["title"] == "Le bouton ne répond pas"
    assert len(_tickets(workspace, "ide-core")) == 1
    assert _tickets(workspace, "mon-projet") == []


def test_idea_creates_a_feat_ticket(workspace: Path) -> None:
    resp = _envoyer(nature="idee")

    assert resp.status_code == 201
    assert resp.json()["type"] == "feat"


def test_ticket_body_carries_origin_and_triage_placeholder() -> None:
    body = _envoyer(contexte="Vu sur la page Kanban").json()["body"]

    assert "## Signalement" in body
    assert "mon-projet" in body
    assert "- [ ] À écrire au triage" in body
    positions = [
        body.index(title)
        for title in (
            "## Signalement",
            "## Description",
            "## Contexte",
            "## Critères d'acceptation",
        )
    ]
    assert positions == sorted(positions)
    assert "Vu sur la page Kanban" in body


def test_context_section_is_omitted_when_not_provided() -> None:
    body = _envoyer().json()["body"]

    assert "## Contexte" not in body
    assert "Rien ne se passe au clic." in body


def test_unknown_source_project_is_404_and_creates_nothing(workspace: Path) -> None:
    resp = _envoyer(projet="inconnu")

    assert resp.status_code == 404
    assert _tickets(workspace, "ide-core") == []


def test_source_project_that_escapes_the_workspace_is_404(workspace: Path) -> None:
    resp = _envoyer(projet="..")

    assert resp.status_code == 404
    assert _tickets(workspace, "ide-core") == []


@pytest.mark.parametrize("titre", ["", "   ", "\n\t"])
def test_blank_title_is_422(workspace: Path, titre: str) -> None:
    resp = _envoyer(titre=titre)

    assert resp.status_code == 422
    assert _tickets(workspace, "ide-core") == []


def test_blank_description_is_422() -> None:
    assert _envoyer(description="  ").status_code == 422


def test_unknown_nature_is_422() -> None:
    assert _envoyer(nature="question").status_code == 422


def test_router_is_mounted_under_api_v1() -> None:
    paths = app.openapi()["paths"]

    assert "post" in paths["/api/v1/signalements"]
