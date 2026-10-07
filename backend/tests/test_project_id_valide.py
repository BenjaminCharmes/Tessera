"""Tests for project_id validation — ticket-370.

Covers the five acceptance criteria:
1. validate_project_id accepts ide-core, cookie_clicker, habit-tracker and
   refuses ., .., ../x, ..\\x (backslash) and the empty string.
2. Every HTTP route with {project_id} returns 404 when project_id is '..'.
3. GET /api/v1/projects/..%5C../tickets returns 404.
4. POST /api/v1/orchestrator/run with project_id='..' returns 422.
5. GET /api/v1/projects/{id}/tickets returns 200 for an existing project.
"""
import asyncio
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.services.database import init_db
from tessera.utils.project_id import validate_project_id


# ------------------------------------------------------------------ fixtures


@pytest.fixture()
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ws = tmp_path / "projects"
    ws.mkdir()
    db_path = tmp_path / "tessera.db"
    asyncio.run(init_db(db_path))
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    monkeypatch.setattr(settings, "ide_db_path", db_path)
    monkeypatch.setattr(settings, "llm_provider", "agent_sdk")
    monkeypatch.setattr(settings, "github_token", "")
    return ws


@pytest.fixture()
def client(workspace: Path) -> TestClient:
    return TestClient(app)


# ------------------------------------------------------------------ criterion 1


def test_validate_project_id_accepts_and_refuses() -> None:
    """validate_project_id accepts known identifiers and refuses unsafe ones."""
    # Accepts: current real project ids must remain accessible.
    assert validate_project_id("ide-core") is True
    assert validate_project_id("cookie_clicker") is True
    assert validate_project_id("habit-tracker") is True
    # Refuses: traversal sequences and the empty string must be blocked.
    assert validate_project_id(".") is False
    assert validate_project_id("..") is False
    assert validate_project_id("../x") is False
    assert validate_project_id(r"..\x") is False   # literal backslash: ..\x
    assert validate_project_id("") is False


# ------------------------------------------------------------------ criterion 2


def test_all_routes_with_project_id_refuse_dotdot(client: TestClient) -> None:
    """Every HTTP route with {project_id} returns 404 when project_id is '..'."""
    schema = app.openapi()
    checked = 0
    for path_template, path_item in schema.get("paths", {}).items():
        if "{project_id}" not in path_template:
            continue
        # Replace project_id with '..' and other params with safe placeholders.
        url = path_template.replace("{project_id}", "..")
        url = re.sub(r"\{[^}]+\}", "placeholder", url)
        for method_str, _operation in path_item.items():
            method = method_str.upper()
            if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                continue
            response = client.request(method, url)
            assert response.status_code == 404, (
                f"{method} {url} returned {response.status_code}, expected 404. "
                f"Body: {response.text[:200]}"
            )
            checked += 1
    assert checked > 0, (
        "No HTTP routes with {project_id} were found — dependency was never tested."
    )


# ------------------------------------------------------------------ criterion 3


def test_url_encoded_backslash_traversal_refused(client: TestClient) -> None:
    """GET /api/v1/projects/..%5C../tickets returns 404."""
    response = client.get("/api/v1/projects/..%5C../tickets")
    assert response.status_code == 404


# ------------------------------------------------------------------ criterion 4


def test_orchestrator_run_refuses_dotdot_project_id(client: TestClient) -> None:
    """POST /api/v1/orchestrator/run with project_id='..' returns 422."""
    response = client.post(
        "/api/v1/orchestrator/run",
        json={"project_id": "..", "ticket_id": "ticket-001", "mode": "single"},
    )
    assert response.status_code == 422


# ------------------------------------------------------------------ criterion 5


def test_tickets_endpoint_returns_200_for_valid_project(workspace: Path) -> None:
    """GET /api/v1/projects/{id}/tickets returns 200 for an existing project."""
    project = workspace / "mon-projet"
    for status in ("todo", "in-progress", "done", "cancelled", "in-review", "blocked"):
        (project / "tickets" / status).mkdir(parents=True)
    (project / "CLAUDE.md").write_text("# mon-projet\n", encoding="utf-8")
    with TestClient(app) as c:
        response = c.get("/api/v1/projects/mon-projet/tickets")
    assert response.status_code == 200


# ------------------------------------------------------------------ revue (corps de création)


def test_validate_project_id_refuses_a_trailing_newline() -> None:
    """A trailing newline is refused: the whole string must match."""
    assert validate_project_id("ide-core\n") is False


@pytest.mark.parametrize(
    ("route", "corps"),
    [
        ("/api/v1/projects", {"project_id": "../hors", "name": "x"}),
        ("/api/v1/projects/import", {"source_path": "C:/nulle-part", "project_id": ".."}),
        ("/api/v1/projects/clone", {"repo_url": "https://github.com/o/r", "project_id": ".."}),
    ],
)
def test_project_creation_bodies_refuse_an_unsafe_id(
    client: TestClient, workspace: Path, route: str, corps: dict[str, str]
) -> None:
    """Creating, importing or cloning a project refuses an id that leaves the projects folder."""
    reponse = client.post(route, json=corps)
    assert reponse.status_code == 422
    assert not (workspace.parent / "hors").exists()
