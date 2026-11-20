"""The intention to run a project's services survives a restart — ticket-890."""
import asyncio
import json
import logging
import sys
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.routers.services_reprise import reprendre_les_services
from tessera.routers.services_running import get_sonde
from tessera.services.noyau.database import init_db
from tessera.services.noyau.services_demandes import demander, lister
from tessera.services.supervision.sonde_systeme import InfoProcessus
from tessera.services.verification.process_registry import PROCESS_REGISTRY, Service

_DORMEUR = f'"{sys.executable}" -c "import time; time.sleep(30)"'


class Sonde:
    def __init__(self, procs: dict[int, InfoProcessus] | None = None) -> None:
        self.procs = procs or {}

    async def ecouteurs(self) -> dict[int, int]:
        return {}

    async def processus(self) -> dict[int, InfoProcessus]:
        return self.procs


@pytest.fixture(autouse=True)
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    ws = tmp_path / "workspace"
    for pid in ("alpha", "beta"):
        projet = ws / pid
        projet.mkdir(parents=True)
        (projet / "CLAUDE.md").write_text(f"# {pid}\n", encoding="utf-8")
        services = [
            {"nom": "api", "commande": _DORMEUR},
            {"nom": "worker", "commande": _DORMEUR},
        ]
        (projet / "agents.json").write_text(
            json.dumps({"project_id": pid, "services": services}), encoding="utf-8"
        )
    db_path = tmp_path / "tessera.db"
    asyncio.run(init_db(db_path))
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    monkeypatch.setattr(settings, "ide_db_path", db_path)
    app.dependency_overrides[get_sonde] = lambda: Sonde()
    yield ws
    asyncio.run(PROCESS_REGISTRY.tout_arreter())
    app.dependency_overrides.clear()


def _inscrits() -> list[str]:
    return asyncio.run(lister(settings.ide_db_path))


def test_start_records_the_project() -> None:
    with TestClient(app) as client:
        resp = client.post("/api/v1/projects/alpha/services/start")
    assert resp.status_code == 200
    assert _inscrits() == ["alpha"]


def test_stop_removes_the_project() -> None:
    with TestClient(app) as client:
        client.post("/api/v1/projects/alpha/services/start")
        resp = client.post("/api/v1/projects/alpha/services/stop")
    assert resp.status_code == 200
    assert _inscrits() == []


def test_resume_starts_each_recorded_project_only() -> None:
    asyncio.run(demander(settings.ide_db_path, "alpha"))
    asyncio.run(demander(settings.ide_db_path, "beta"))
    registre = MagicMock()
    registre.demarrer = AsyncMock(return_value=Service(nom='api', project_id='x'))
    asyncio.run(reprendre_les_services(settings.ide_db_path, Sonde(), registre))
    projets = [c.args[0] for c in registre.demarrer.await_args_list]
    assert sorted(projets) == ["alpha", "alpha", "beta", "beta"]


def test_resume_skips_a_project_absent_from_the_table() -> None:
    asyncio.run(demander(settings.ide_db_path, "beta"))
    registre = MagicMock()
    registre.demarrer = AsyncMock(return_value=Service(nom='api', project_id='x'))
    asyncio.run(reprendre_les_services(settings.ide_db_path, Sonde(), registre))
    assert {c.args[0] for c in registre.demarrer.await_args_list} == {"beta"}


def test_a_failing_project_is_logged_dropped_and_the_next_is_resumed(
    caplog: pytest.LogCaptureFixture,
) -> None:
    asyncio.run(demander(settings.ide_db_path, "alpha"))
    asyncio.run(demander(settings.ide_db_path, "beta"))

    async def demarrer(project_id: str, *_: object, **__: object) -> Service:
        if project_id == "alpha":
            raise RuntimeError("boom")
        return Service(nom='api', project_id='x')

    registre = MagicMock()
    registre.demarrer = AsyncMock(side_effect=demarrer)
    with caplog.at_level(logging.WARNING):
        asyncio.run(reprendre_les_services(settings.ide_db_path, Sonde(), registre))
    assert _inscrits() == ["beta"]
    assert any(r.getMessage() == "services_non_repris" for r in caplog.records)
    assert "beta" in {c.args[0] for c in registre.demarrer.await_args_list}


def test_a_service_already_running_outside_tessera_is_not_resumed(
    workspace: Path,
) -> None:
    asyncio.run(demander(settings.ide_db_path, "alpha"))
    manifeste = workspace / "alpha" / "agents.json"
    manifeste.write_text(
        json.dumps(
            {"project_id": "alpha", "services": [{"nom": "worker", "commande": "python -m app.worker"}]}
        ),
        encoding="utf-8",
    )
    commande = f'"{workspace / "alpha" / ".venv" / "python.exe"}" -m app.worker'
    procs = {4242: InfoProcessus(ppid=1, memoire_mo=1.0, demarre_a=None, commande=commande)}
    registre = MagicMock()
    registre.demarrer = AsyncMock()
    asyncio.run(reprendre_les_services(settings.ide_db_path, Sonde(procs), registre))
    registre.demarrer.assert_not_awaited()
    assert _inscrits() == []
