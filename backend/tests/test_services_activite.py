"""`GET /services/running/activite` — ticket-671, ADR-064.

La sonde est un faux, comme dans `test_services_running.py` : une app « tourne »
quand un port déclaré est écouté par un processus du projet.
"""
import asyncio
import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.routers.services_running import get_sonde
from tessera.services.database import init_db
from tessera.services.sonde_systeme import InfoProcessus


@dataclass
class FausseSonde:
    ports: dict[int, int] = field(default_factory=dict)
    procs: dict[int, InfoProcessus] = field(default_factory=dict)

    async def ecouteurs(self) -> dict[int, int]:
        return self.ports

    async def processus(self) -> dict[int, InfoProcessus]:
        return self.procs


@pytest.fixture(autouse=True)
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ws = tmp_path / "workspace"
    projet = ws / "mon-projet"
    (projet / "memory").mkdir(parents=True)
    (projet / "CLAUDE.md").write_text("# Mon projet\n", encoding="utf-8")
    db_path = tmp_path / "tessera.db"
    asyncio.run(init_db(db_path))
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    monkeypatch.setattr(settings, "ide_db_path", db_path)
    monkeypatch.setattr(settings, "llm_provider", "agent_sdk")
    return ws


@pytest.fixture(autouse=True)
def _nettoyer() -> Iterator[None]:
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


def _declarer(projet: Path) -> None:
    services = [
        {
            "nom": "worker",
            "commande": "uvicorn x:app --port 8026",
            "activite": "data/activite.json",
        },
        {"nom": "web", "commande": "vite --port 8027"},
    ]
    (projet / "agents.json").write_text(
        json.dumps({"project_id": projet.name, "services": services}),
        encoding="utf-8",
    )


def _ecrire_activite(projet: Path) -> None:
    maintenant = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    contenu = {
        "version": 1,
        "maj": maintenant,
        "agents": [{"id": "triage", "nom": "Triage", "etat": "actif"}],
    }
    cible = projet / "data" / "activite.json"
    cible.parent.mkdir(parents=True, exist_ok=True)
    cible.write_text(json.dumps(contenu), encoding="utf-8")


def _faire_tourner(workspace: Path, ports: list[int]) -> None:
    commande = f'python "{workspace / "mon-projet" / "api.py"}"'
    procs = {
        4000 + i: InfoProcessus(ppid=1, memoire_mo=10.0, demarre_a=None, commande=commande)
        for i, _ in enumerate(ports)
    }
    sonde = FausseSonde(
        ports={p: 4000 + i for i, p in enumerate(ports)}, procs=procs
    )
    app.dependency_overrides[get_sonde] = lambda: sonde


def _lire(client: TestClient) -> list[dict[str, object]]:
    resp = client.get("/api/v1/services/running/activite")
    assert resp.status_code == 200, resp.text
    body: list[dict[str, object]] = resp.json()
    return body


def test_running_service_with_a_fresh_file_returns_its_agents(
    client: TestClient, workspace: Path
) -> None:
    projet = workspace / "mon-projet"
    _declarer(projet)
    _ecrire_activite(projet)
    _faire_tourner(workspace, [8026])

    entrees = _lire(client)

    assert len(entrees) == 1
    assert entrees[0]["project_id"] == "mon-projet"
    assert entrees[0]["service"] == "worker"
    agents = entrees[0]["agents"]
    assert isinstance(agents, list) and agents[0]["id"] == "triage"


def test_service_whose_app_is_not_running_returns_nothing_despite_a_fresh_file(
    client: TestClient, workspace: Path
) -> None:
    projet = workspace / "mon-projet"
    _declarer(projet)
    _ecrire_activite(projet)
    _faire_tourner(workspace, [])

    assert _lire(client) == []


def test_running_service_without_a_declared_file_has_no_entry(
    client: TestClient, workspace: Path
) -> None:
    projet = workspace / "mon-projet"
    _declarer(projet)
    _faire_tourner(workspace, [8027])

    assert _lire(client) == []


def test_running_service_with_a_missing_file_has_an_entry_without_agents(
    client: TestClient, workspace: Path
) -> None:
    _declarer(workspace / "mon-projet")
    _faire_tourner(workspace, [8026])

    entrees = _lire(client)

    assert [(e["service"], e["agents"]) for e in entrees] == [("worker", [])]
