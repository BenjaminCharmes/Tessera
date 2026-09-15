"""Suivi de ce qu'un ticket a produit — ticket-064."""
import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vibe_ide.config import settings
from vibe_ide.main import app
from vibe_ide.services.database import create_run, finish_run, init_db

_TICKET = """---
id: {id}
title: "Un ticket"
type: feat
status: todo
priority: medium
agent: codeur
{extra}---

# {id} — Un ticket

## Objectif

Faire la chose.
"""


@pytest.fixture(autouse=True)
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ws = tmp_path / "workspace"
    project = ws / "mon-projet"
    (project / "memory").mkdir(parents=True)
    (project / "CLAUDE.md").write_text("# p\n", encoding="utf-8")
    for st in ("todo", "in-progress", "in-review", "done", "blocked"):
        (project / "tickets" / st).mkdir(parents=True)
    (project / "tickets" / "todo" / "ticket-042.md").write_text(
        _TICKET.format(id="ticket-042", extra=""), encoding="utf-8"
    )

    db_path = tmp_path / "vibe.db"
    asyncio.run(init_db(db_path))
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    monkeypatch.setattr(settings, "ide_db_path", db_path)
    monkeypatch.setattr(settings, "github_token", "")
    return ws


def _client() -> TestClient:
    return TestClient(app)


def test_un_ticket_sans_run_n_a_rien_a_montrer(workspace: Path) -> None:
    body = _client().get("/api/v1/projects/mon-projet/tickets/ticket-042/activity").json()

    assert body["ticket_id"] == "ticket-042"
    assert body["runs"] == []
    assert body["pr_number"] is None


def test_les_runs_du_ticket_sont_rassembles(workspace: Path) -> None:
    # L'information existait, éparpillée entre la base et le ticket : il
    # fallait sortir de l'IDE et lire `git log` pour savoir ce qu'un ticket
    # avait produit.
    async def _seed() -> None:
        run_id = await create_run(settings.ide_db_path, "mon-projet", "ticket-042")
        await finish_run(settings.ide_db_path, run_id, 2, True, "done")

    asyncio.run(_seed())

    body = _client().get("/api/v1/projects/mon-projet/tickets/ticket-042/activity").json()

    assert len(body["runs"]) == 1
    assert body["runs"][0]["rounds"] == 2
    assert body["runs"][0]["approved"] is True


def test_la_pr_du_ticket_est_remontee(workspace: Path) -> None:
    (workspace / "mon-projet" / "tickets" / "todo" / "ticket-043.md").write_text(
        _TICKET.format(id="ticket-043", extra="pr_number: 12\n"), encoding="utf-8"
    )

    body = _client().get("/api/v1/projects/mon-projet/tickets/ticket-043/activity").json()

    assert body["pr_number"] == 12


def test_un_ticket_inexistant_renvoie_404(workspace: Path) -> None:
    resp = _client().get("/api/v1/projects/mon-projet/tickets/ticket-999/activity")
    assert resp.status_code == 404


def test_ouvrir_une_pr_sans_github_est_refuse(workspace: Path) -> None:
    resp = _client().post(
        "/api/v1/projects/mon-projet/tickets/ticket-042/open-pr",
        json={"branch": "ticket-042-slug"},
    )

    assert resp.status_code == 422
    assert "github" in resp.json()["detail"].lower()


def test_ouvrir_une_pr_pousse_puis_cree(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # L'ordre est le correctif du ticket : GitHub refuse une `head` inconnue.
    import json

    (workspace / "mon-projet" / "agents.json").write_text(
        json.dumps({"github_remote": "owner/repo"}), encoding="utf-8"
    )
    monkeypatch.setattr(settings, "github_token", "ghp_test")

    calls: list[str] = []

    async def _push(self: object, branch: str) -> None:
        calls.append(f"push:{branch}")

    async def _create(self: object, **kwargs: object) -> tuple[int, str]:
        calls.append("create-pr")
        return 7, "https://github.com/owner/repo/pull/7"

    monkeypatch.setattr(
        "vibe_ide.services.git_workspace.GitWorkspaceService.push_branch", _push
    )
    monkeypatch.setattr(
        "vibe_ide.services.github_service.GitHubService.create_pull_request", _create
    )

    resp = _client().post(
        "/api/v1/projects/mon-projet/tickets/ticket-042/open-pr",
        json={"branch": "ticket-042-slug"},
    )

    assert resp.status_code == 200
    assert resp.json()["pr_number"] == 7
    assert calls == ["push:ticket-042-slug", "create-pr"]
