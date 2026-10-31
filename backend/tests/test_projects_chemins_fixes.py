"""Fixed paths of the projects router win over `/{project_id}` — ticket-689.

Découper le routeur par ressource change l'ordre d'enregistrement des routes :
un chemin fixe lu après `/{project_id}` serait pris pour un identifiant de
projet et rendrait un 404 de projet. Ce test appelle chaque chemin fixe.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.services.database import init_db

BASE = "/api/v1/projects"


@pytest.fixture
async def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    base = tmp_path / "tessera.db"
    await init_db(base)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setattr(settings, "ide_db_path", base)
    monkeypatch.setattr(settings, "ide_workspace_dir", workspace)
    return TestClient(app)


def test_overview_is_served_by_its_own_route(client: TestClient) -> None:
    with client:
        response = client.get(f"{BASE}/overview")

    assert response.status_code == 200
    assert response.json() == []


def test_global_usage_breakdown_is_served_by_its_own_route(client: TestClient) -> None:
    with client:
        response = client.get(f"{BASE}/usage/breakdown")

    assert response.status_code == 200
    assert response.json()["project_id"] is None


@pytest.mark.parametrize("chemin", ["import", "clone", "from-template"])
def test_fixed_post_paths_reach_their_handler(client: TestClient, chemin: str) -> None:
    """A body check (422) proves the route matched: no project lookup is involved."""
    with client:
        response = client.post(f"{BASE}/{chemin}", json={})

    assert response.status_code == 422
