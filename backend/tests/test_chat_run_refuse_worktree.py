"""The chat never runs a project that declares a worktree — ticket-999 (ADR-056)."""
import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    projet = tmp_path / "ws" / "mon-projet"
    (projet / "tickets" / "todo").mkdir(parents=True)
    manifeste = {"artifacts": "tracked", "base_branch": "develop", "worktree": {}}
    (projet / "agents.json").write_text(json.dumps(manifeste), encoding="utf-8")
    monkeypatch.setattr(settings, "ide_workspace_dir", tmp_path / "ws")
    monkeypatch.setattr(settings, "ide_db_path", tmp_path / "t.db")
    with TestClient(app) as c:
        yield c


def test_chat_run_on_a_worktree_project_is_refused_without_any_call(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    appels: list[str] = []

    async def _build(project_id: str) -> None:
        appels.append(project_id)

    monkeypatch.setattr("tessera.routers.chat.build_orchestrator", _build)
    reponse = client.post(
        "/api/v1/projects/mon-projet/chat/run",
        json={"ticket_id": "ticket-001", "conversation_id": "c1"},
    )
    assert reponse.status_code == 409, reponse.text
    assert "worktree" in reponse.json()["detail"]
    assert appels == []
