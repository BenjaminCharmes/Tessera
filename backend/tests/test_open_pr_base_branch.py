"""open-pr uses the project's declared base branch — ticket-269."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app

_TICKET_MD = """---
id: ticket-001
title: "Un ticket"
type: feat
status: todo
priority: medium
agent: codeur
---

# ticket-001 — Un ticket
"""


@pytest.fixture(autouse=True)
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ws = tmp_path / "workspace"
    project = ws / "mon-projet"
    (project / "memory").mkdir(parents=True)
    (project / "CLAUDE.md").write_text("# mon-projet\n", encoding="utf-8")
    for status in ("todo", "in-progress", "in-review", "done", "blocked", "archive"):
        (project / "tickets" / status).mkdir(parents=True)
    (project / "tickets" / "todo" / "ticket-001.md").write_text(_TICKET_MD, encoding="utf-8")
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    monkeypatch.setattr(settings, "github_token", "ghp_test")
    monkeypatch.setattr(settings, "github_base_branch", "develop")
    return ws


def _client() -> TestClient:
    return TestClient(app)


def _set_agents_json(ws: Path, data: dict) -> None:  # type: ignore[type-arg]
    (ws / "mon-projet" / "agents.json").write_text(json.dumps(data), encoding="utf-8")


def _make_fake_open_pr(captured: dict) -> object:  # type: ignore[type-arg]
    """Returns a coroutine that records the base_branch passed to GitHubWorkflowService."""

    from tessera.services.github_workflow import PullRequestResult

    async def _fake_open(
        self: object,
        branch: str,
        ticket_id: str,
        ticket_title: str,
        ticket_body: str,
        ticket_type: str,
        autonome: bool = False,
    ) -> PullRequestResult:
        captured["base_branch"] = self._base_branch  # type: ignore[attr-defined]
        return PullRequestResult(pr_number=42, pr_url="https://example.com/pull/42", branch=branch)

    return _fake_open


def test_open_pr_uses_declared_base_branch(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """open-pr on a project declaring base_branch=main passes main as base."""
    _set_agents_json(workspace, {"github_remote": "owner/repo", "base_branch": "main"})

    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "tessera.services.github_workflow.GitHubWorkflowService.open_pull_request",
        _make_fake_open_pr(captured),
    )

    resp = _client().post(
        "/api/v1/projects/mon-projet/tickets/ticket-001/open-pr",
        json={"branch": "ticket-001-slug"},
    )

    assert resp.status_code == 200
    assert captured["base_branch"] == "main"


def test_open_pr_falls_back_to_settings_when_no_base_branch_declared(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """open-pr on a project without base_branch passes settings.github_base_branch."""
    _set_agents_json(workspace, {"github_remote": "owner/repo"})

    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "tessera.services.github_workflow.GitHubWorkflowService.open_pull_request",
        _make_fake_open_pr(captured),
    )

    resp = _client().post(
        "/api/v1/projects/mon-projet/tickets/ticket-001/open-pr",
        json={"branch": "ticket-001-slug"},
    )

    assert resp.status_code == 200
    assert captured["base_branch"] == "develop"
