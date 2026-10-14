"""L'inventaire des apps de projet qui tournent — ticket-416.

La sonde système est un faux : ce qui s'écoute sur la machine de test ne
doit rien changer au résultat. Le service « vivant » du registre, lui, est un
vrai processus, lancé par l'API comme dans `test_services_du_projet.py`.
"""
import asyncio
import json
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.routers import services_running
from tessera.routers.services_running import get_sonde
from tessera.services.database import init_db
from tessera.services.process_registry import PROCESS_REGISTRY
from tessera.services.sonde_systeme import InfoProcessus

_DORMEUR = f'"{sys.executable}" -c "import time; time.sleep(30)"'


@dataclass
class FausseSonde:
    """Une machine décrite à la main : ports en écoute et processus."""

    ports: dict[int, int] = field(default_factory=dict)
    procs: dict[int, InfoProcessus] = field(default_factory=dict)

    async def ecouteurs(self) -> dict[int, int]:
        return self.ports

    async def processus(self) -> dict[int, InfoProcessus]:
        return self.procs


def _info(ppid: int, memoire_mo: float, commande: str = "") -> InfoProcessus:
    return InfoProcessus(
        ppid=ppid, memoire_mo=memoire_mo, demarre_a=None, commande=commande
    )


def _du_projet(workspace: Path) -> str:
    """Une ligne de commande qui désigne un fichier du projet (ticket-435)."""
    return f'python "{workspace / "mon-projet" / "api.py"}"'


def _declarer(projet: Path, services: list[dict[str, str]]) -> None:
    projet.joinpath("agents.json").write_text(
        json.dumps({"project_id": projet.name, "services": services}),
        encoding="utf-8",
    )


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
def _arreter_tout() -> Iterator[None]:
    yield
    asyncio.run(PROCESS_REGISTRY.tout_arreter())
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


def _sonde(sonde: FausseSonde) -> None:
    app.dependency_overrides[get_sonde] = lambda: sonde


def _lister(client: TestClient) -> list[dict[str, object]]:
    resp = client.get("/api/v1/services/running")
    assert resp.status_code == 200, resp.text
    body: list[dict[str, object]] = resp.json()
    return body


def test_live_registry_service_is_listed_as_tessera(
    client: TestClient, workspace: Path
) -> None:
    _declarer(
        workspace / "mon-projet",
        [{"nom": "api", "commande": f"{_DORMEUR} --port 8026"}],
    )
    client.post("/api/v1/projects/mon-projet/services/start")
    pid = PROCESS_REGISTRY.services_de("mon-projet")[0].pid
    assert pid is not None
    # Un enfant : sa mémoire s'ajoute à celle du service.
    _sonde(FausseSonde(procs={pid: _info(1, 10.0), pid + 1: _info(pid, 5.5)}))

    apps = _lister(client)

    assert len(apps) == 1
    assert apps[0]["origine"] == "tessera"
    assert apps[0]["pid"] == pid
    assert apps[0]["project_id"] == "mon-projet"
    assert apps[0]["project_name"] == "Mon projet"
    assert apps[0]["ports"] == [8026]
    assert apps[0]["memoire_mo"] == 15.5


def test_process_on_declared_port_is_listed_as_external(
    client: TestClient, workspace: Path
) -> None:
    _declarer(
        workspace / "mon-projet",
        [{"nom": "api", "commande": "uvicorn x:app --port 8026"}],
    )
    _sonde(
        FausseSonde(
            ports={8026: 4242}, procs={4242: _info(1, 80.0, _du_projet(workspace))}
        )
    )

    apps = _lister(client)

    assert len(apps) == 1
    assert apps[0]["origine"] == "externe"
    assert apps[0]["project_id"] == "mon-projet"
    assert apps[0]["nom"] == "api"
    assert apps[0]["pid"] == 4242
    assert apps[0]["memoire_mo"] == 80.0


def test_undeclared_port_is_not_listed(client: TestClient, workspace: Path) -> None:
    _declarer(workspace / "mon-projet", [{"nom": "api", "commande": "x --port 8026"}])
    _sonde(FausseSonde(ports={9999: 4242}, procs={4242: _info(1, 80.0)}))

    assert _lister(client) == []


def test_process_on_two_ports_is_listed_once(
    client: TestClient, workspace: Path
) -> None:
    _declarer(
        workspace / "mon-projet",
        [
            {"nom": "api", "commande": "x --port 8026"},
            {"nom": "admin", "commande": "y --port 8027"},
        ],
    )
    _sonde(
        FausseSonde(
            ports={8026: 4242, 8027: 4242},
            procs={4242: _info(1, 1.0, _du_projet(workspace))},
        )
    )

    apps = _lister(client)

    assert len(apps) == 1
    assert apps[0]["ports"] == [8026, 8027]


def test_descendant_of_a_tessera_service_is_not_listed_twice(
    client: TestClient, workspace: Path
) -> None:
    _declarer(
        workspace / "mon-projet",
        [{"nom": "api", "commande": f"{_DORMEUR} --port 8026"}],
    )
    client.post("/api/v1/projects/mon-projet/services/start")
    pid = PROCESS_REGISTRY.services_de("mon-projet")[0].pid
    assert pid is not None
    # L'enfant, et non le service, écoute le port déclaré.
    enfant = pid + 1
    _sonde(
        FausseSonde(
            ports={8026: enfant}, procs={pid: _info(1, 2.0), enfant: _info(pid, 3.0)}
        )
    )

    apps = _lister(client)

    assert [a["origine"] for a in apps] == ["tessera"]


def test_tessera_own_ports_are_excluded(client: TestClient, workspace: Path) -> None:
    (workspace / "mon-projet" / "frontend").mkdir()
    (workspace / "mon-projet" / "frontend" / "vite.config.ts").write_text(
        "export default { server: { port: 5173 } }", encoding="utf-8"
    )
    _declarer(workspace / "mon-projet", [{"nom": "back", "commande": "x --port 8100"}])
    _sonde(
        FausseSonde(
            ports={8100: 111, 5173: 222}, procs={111: _info(1, 9.0), 222: _info(1, 9.0)}
        )
    )

    assert _lister(client) == []


def test_stop_unknown_pid_is_404_and_stops_nothing(
    client: TestClient, workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _declarer(workspace / "mon-projet", [{"nom": "api", "commande": "x --port 8026"}])
    appels: list[int] = []

    async def _tuer(pid: int) -> bool:
        appels.append(pid)
        return True

    monkeypatch.setattr(services_running, "tuer_l_arbre", _tuer)
    _sonde(FausseSonde(ports={8026: 4242}, procs={4242: _info(1, 1.0)}))

    resp = client.post("/api/v1/services/running/777/stop")

    assert resp.status_code == 404
    assert appels == []


def test_stop_listed_external_pid_kills_its_tree(
    client: TestClient, workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _declarer(workspace / "mon-projet", [{"nom": "api", "commande": "x --port 8026"}])
    appels: list[int] = []

    async def _tuer(pid: int) -> bool:
        appels.append(pid)
        return True

    monkeypatch.setattr(services_running, "tuer_l_arbre", _tuer)
    _sonde(
        FausseSonde(
            ports={8026: 4242}, procs={4242: _info(1, 1.0, _du_projet(workspace))}
        )
    )

    resp = client.post("/api/v1/services/running/4242/stop")

    assert resp.status_code == 200
    assert appels == [4242]


def test_stop_tessera_service_goes_through_the_registry(
    client: TestClient, workspace: Path
) -> None:
    _declarer(workspace / "mon-projet", [{"nom": "api", "commande": _DORMEUR}])
    client.post("/api/v1/projects/mon-projet/services/start")
    pid = PROCESS_REGISTRY.services_de("mon-projet")[0].pid
    assert pid is not None
    _sonde(FausseSonde(procs={pid: _info(1, 1.0)}))

    resp = client.post(f"/api/v1/services/running/{pid}/stop")

    assert resp.status_code == 200
    assert resp.json()["arretes"] == 1
    assert PROCESS_REGISTRY.vivants() == []
