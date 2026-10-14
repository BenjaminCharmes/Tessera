"""Une app étrangère n'est jamais attribuée à un projet — ticket-435.

Un port déclaré, occupé par un programme qui n'a rien à voir avec le projet,
ne doit pas devenir un bouton « Arrêter ». La sonde est un faux.
"""
import asyncio
import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.routers import services_running
from tessera.routers.services_running import get_sonde
from tessera.services import inventaire_apps
from tessera.services.attribution_processus import appartient_au_projet
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


def _proc(ppid: int = 1, commande: str = "") -> InfoProcessus:
    return InfoProcessus(ppid=ppid, memoire_mo=10.0, demarre_a=None, commande=commande)


@pytest.fixture(autouse=True)
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ws = tmp_path / "workspace"
    projet = ws / "mon-projet"
    (projet / "memory").mkdir(parents=True)
    (projet / "CLAUDE.md").write_text("# Mon projet\n", encoding="utf-8")
    (projet / "agents.json").write_text(
        json.dumps(
            {
                "project_id": "mon-projet",
                "services": [{"nom": "api", "commande": "uvicorn x:app --port 8026"}],
            }
        ),
        encoding="utf-8",
    )
    db_path = tmp_path / "tessera.db"
    asyncio.run(init_db(db_path))
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    monkeypatch.setattr(settings, "ide_db_path", db_path)
    monkeypatch.setattr(settings, "llm_provider", "agent_sdk")
    return ws


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _sonde(sonde: FausseSonde) -> None:
    app.dependency_overrides[get_sonde] = lambda: sonde


def _lister(client: TestClient) -> list[dict[str, object]]:
    resp = client.get("/api/v1/services/running")
    assert resp.status_code == 200, resp.text
    body: list[dict[str, object]] = resp.json()
    return body


def _etranger(workspace: Path) -> FausseSonde:
    """Un programme hors du projet (ni commande ni parent sous son dossier)."""
    ailleurs = workspace.parent / "ailleurs" / "serveur.py"
    return FausseSonde(
        ports={8026: 4242},
        procs={4242: _proc(7, f'python "{ailleurs}"'), 7: _proc(1, "explorer.exe")},
    )


def test_process_outside_the_project_is_not_one_of_its_apps(
    client: TestClient, workspace: Path
) -> None:
    _sonde(_etranger(workspace))

    assert _lister(client) == []


def test_process_whose_command_is_under_the_project_stays_attributed(
    client: TestClient, workspace: Path
) -> None:
    commande = f'python "{workspace / "mon-projet" / "backend" / "main.py"}"'
    _sonde(FausseSonde(ports={8026: 4242}, procs={4242: _proc(1, commande)}))

    apps = _lister(client)

    assert [(a["origine"], a["pid"]) for a in apps] == [("externe", 4242)]


def test_process_whose_direct_parent_is_under_the_project_stays_attributed(
    client: TestClient, workspace: Path
) -> None:
    parent = f'npm --prefix "{workspace / "mon-projet" / "frontend"}" run dev'
    _sonde(
        FausseSonde(
            ports={8026: 4242}, procs={4242: _proc(7, "node vite.js"), 7: _proc(1, parent)}
        )
    )

    assert [a["pid"] for a in _lister(client)] == [4242]


def test_foreign_port_is_a_warning_without_a_stoppable_pid(
    client: TestClient, workspace: Path
) -> None:
    _sonde(_etranger(workspace))

    resp = client.get("/api/v1/services/running/avertissements")

    assert resp.status_code == 200
    avertissements = resp.json()
    assert len(avertissements) == 1
    assert avertissements[0]["project_id"] == "mon-projet"
    assert avertissements[0]["port"] == 8026
    assert "occupé par un autre programme" in avertissements[0]["message"]
    assert "pid" not in avertissements[0]


def test_attributed_process_gives_no_warning(
    client: TestClient, workspace: Path
) -> None:
    commande = f'python "{workspace / "mon-projet" / "api.py"}"'
    _sonde(FausseSonde(ports={8026: 4242}, procs={4242: _proc(1, commande)}))

    assert client.get("/api/v1/services/running/avertissements").json() == []


def test_stop_of_a_foreign_pid_is_404_and_kills_nothing(
    client: TestClient, workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    appels: list[int] = []

    async def _tuer(pid: int) -> bool:
        appels.append(pid)
        return True

    monkeypatch.setattr(services_running, "tuer_l_arbre", _tuer)
    _sonde(_etranger(workspace))

    resp = client.post("/api/v1/services/running/4242/stop")

    assert resp.status_code == 404
    assert appels == []


def test_project_running_the_ide_has_no_external_app(
    client: TestClient, workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(inventaire_apps, "fait_tourner_l_ide", lambda path: True)
    commande = f'python "{workspace / "mon-projet" / "api.py"}"'
    _sonde(FausseSonde(ports={8026: 4242}, procs={4242: _proc(1, commande)}))

    assert _lister(client) == []
    assert client.get("/api/v1/services/running/avertissements").json() == []


def test_sibling_folder_with_the_same_prefix_is_not_the_project(
    tmp_path: Path,
) -> None:
    racine = tmp_path / "projets" / "ide"
    voisin = f'node "{tmp_path / "projets" / "ide-core" / "x.js"}"'

    assert not appartient_au_projet(5, racine, {5: _proc(1, voisin)})


def test_unknown_pid_or_empty_command_is_not_attributed(tmp_path: Path) -> None:
    assert not appartient_au_projet(5, tmp_path, {})
    assert not appartient_au_projet(5, tmp_path, {5: _proc(1, "")})


def test_forward_slashes_in_a_command_line_are_recognised(tmp_path: Path) -> None:
    racine = tmp_path / "Projet"
    commande = f"node {racine.as_posix()}/x.js"

    assert appartient_au_projet(5, racine, {5: _proc(1, commande)})
