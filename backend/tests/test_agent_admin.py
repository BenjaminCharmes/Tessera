"""Tests d'intégration pour le router /api/v1/agents/registry."""
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vibe_ide.routers.agent_admin import get_registry, router
from vibe_ide.services.agent_registry import AgentRegistryService

BASE = "/api/v1/agents/registry"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_client(prompts_dir: Path) -> TestClient:
    """Construit une app FastAPI isolée avec le router agent_admin."""
    registry = AgentRegistryService(prompts_dir)
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_registry] = lambda: registry
    return TestClient(app)


@pytest.fixture()
def prompts_dir(tmp_path: Path) -> Path:
    d = tmp_path / "prompts"
    d.mkdir()
    return d


@pytest.fixture()
def client(prompts_dir: Path) -> TestClient:
    return _make_client(prompts_dir)


@pytest.fixture()
def client_with_custom(prompts_dir: Path) -> TestClient:
    (prompts_dir / "traducteur.md").write_text("Tu traduis.", encoding="utf-8")
    (prompts_dir / "codeur.md").write_text("Tu codes.", encoding="utf-8")
    return _make_client(prompts_dir)


# ---------------------------------------------------------------------------
# GET /agents/registry — list
# ---------------------------------------------------------------------------


def test_list_returns_200(client: TestClient) -> None:
    resp = client.get(BASE)
    assert resp.status_code == 200


def test_list_contains_builtins(client: TestClient) -> None:
    data = client.get(BASE).json()
    roles = {a["role"] for a in data["agents"]}
    assert "codeur" in roles
    assert "reviewer" in roles
    assert "orchestrateur" in roles


def test_list_marks_builtins(client: TestClient) -> None:
    data = client.get(BASE).json()
    by_role = {a["role"]: a for a in data["agents"]}
    assert by_role["codeur"]["is_builtin"] is True
    assert by_role["reviewer"]["is_builtin"] is True


def test_list_includes_custom_agent(client_with_custom: TestClient) -> None:
    data = client_with_custom.get(BASE).json()
    by_role = {a["role"]: a for a in data["agents"]}
    assert "traducteur" in by_role
    assert by_role["traducteur"]["is_builtin"] is False


def test_list_prompt_preview_200_chars(prompts_dir: Path) -> None:
    long_prompt = "A" * 500
    (prompts_dir / "verbose.md").write_text(long_prompt, encoding="utf-8")
    cl = _make_client(prompts_dir)
    data = cl.get(BASE).json()
    by_role = {a["role"]: a for a in data["agents"]}
    assert len(by_role["verbose"]["prompt_preview"]) == 200


def test_list_prompt_preview_empty_when_no_file(client: TestClient) -> None:
    data = client.get(BASE).json()
    by_role = {a["role"]: a for a in data["agents"]}
    # Built-ins without a prompt file have empty preview
    assert by_role["reviewer"]["prompt_preview"] == ""


# ---------------------------------------------------------------------------
# GET /agents/registry/{role} — detail
# ---------------------------------------------------------------------------


def test_get_agent_returns_prompt(client_with_custom: TestClient) -> None:
    resp = client_with_custom.get(f"{BASE}/traducteur")
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "traducteur"
    assert data["system_prompt"] == "Tu traduis."
    assert data["is_builtin"] is False


def test_get_builtin_agent(client_with_custom: TestClient) -> None:
    resp = client_with_custom.get(f"{BASE}/codeur")
    assert resp.status_code == 200
    assert resp.json()["is_builtin"] is True
    assert resp.json()["system_prompt"] == "Tu codes."


def test_get_unknown_agent_returns_404(client: TestClient) -> None:
    resp = client.get(f"{BASE}/fantome")
    assert resp.status_code == 404


def test_get_invalid_role_returns_422(client: TestClient) -> None:
    resp = client.get(f"{BASE}/../secrets")
    # FastAPI re-routes path traversal attempts; the slash makes it hit a different path.
    # Either 404 or 422 is acceptable.
    assert resp.status_code in (404, 422)


# ---------------------------------------------------------------------------
# POST /agents/registry — create
# ---------------------------------------------------------------------------


def test_create_agent_returns_201(client: TestClient) -> None:
    resp = client.post(BASE, json={"role": "redacteur", "system_prompt": "Tu rédiges."})
    assert resp.status_code == 201


def test_create_agent_response_body(client: TestClient) -> None:
    resp = client.post(BASE, json={"role": "redacteur", "system_prompt": "Tu rédiges."})
    data = resp.json()
    assert data["role"] == "redacteur"
    assert data["is_builtin"] is False
    assert data["prompt_preview"] == "Tu rédiges."


def test_create_agent_persists(prompts_dir: Path) -> None:
    cl = _make_client(prompts_dir)
    cl.post(BASE, json={"role": "analyseur", "system_prompt": "Tu analyses."})
    assert (prompts_dir / "analyseur.md").exists()
    assert (prompts_dir / "analyseur.md").read_text(encoding="utf-8") == "Tu analyses."


def test_create_agent_overwrites_existing(prompts_dir: Path) -> None:
    (prompts_dir / "redacteur.md").write_text("v1", encoding="utf-8")
    cl = _make_client(prompts_dir)
    resp = cl.post(BASE, json={"role": "redacteur", "system_prompt": "v2"})
    assert resp.status_code == 201
    assert (prompts_dir / "redacteur.md").read_text(encoding="utf-8") == "v2"


def test_create_agent_invalid_role_uppercase(client: TestClient) -> None:
    resp = client.post(BASE, json={"role": "Redacteur", "system_prompt": "prompt"})
    assert resp.status_code == 422


def test_create_agent_invalid_role_starts_with_digit(client: TestClient) -> None:
    resp = client.post(BASE, json={"role": "1agent", "system_prompt": "prompt"})
    assert resp.status_code == 422


def test_create_agent_invalid_role_path_traversal(client: TestClient) -> None:
    resp = client.post(BASE, json={"role": "../evil", "system_prompt": "malicious"})
    assert resp.status_code == 422


def test_create_agent_empty_prompt_rejected(client: TestClient) -> None:
    resp = client.post(BASE, json={"role": "redacteur", "system_prompt": "   "})
    assert resp.status_code == 422


def test_create_agent_hyphenated_role_accepted(client: TestClient) -> None:
    resp = client.post(BASE, json={"role": "mon-agent", "system_prompt": "prompt"})
    assert resp.status_code == 201


# ---------------------------------------------------------------------------
# DELETE /agents/registry/{role} — delete
# ---------------------------------------------------------------------------


def test_delete_custom_agent_returns_204(prompts_dir: Path) -> None:
    (prompts_dir / "traducteur.md").write_text("Tu traduis.", encoding="utf-8")
    cl = _make_client(prompts_dir)
    resp = cl.delete(f"{BASE}/traducteur")
    assert resp.status_code == 204


def test_delete_removes_file(prompts_dir: Path) -> None:
    (prompts_dir / "traducteur.md").write_text("Tu traduis.", encoding="utf-8")
    cl = _make_client(prompts_dir)
    cl.delete(f"{BASE}/traducteur")
    assert not (prompts_dir / "traducteur.md").exists()


def test_delete_builtin_returns_403(client: TestClient) -> None:
    resp = client.delete(f"{BASE}/codeur")
    assert resp.status_code == 403
    assert "built-in" in resp.json()["detail"].lower()


def test_delete_builtin_reviewer_returns_403(client: TestClient) -> None:
    resp = client.delete(f"{BASE}/reviewer")
    assert resp.status_code == 403


def test_delete_unknown_returns_404(client: TestClient) -> None:
    resp = client.delete(f"{BASE}/fantome")
    assert resp.status_code == 404


def test_delete_invalid_role_path_traversal(client: TestClient) -> None:
    # Path traversal in URL path is caught by the regex check in the handler
    # or by routing (FastAPI splits on /)
    resp = client.delete(f"{BASE}/..%2Fsecrets")
    assert resp.status_code in (404, 422)
