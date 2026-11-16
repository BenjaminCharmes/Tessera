"""A project service never starts on a port Tessera uses — ticket-967."""
import asyncio
import json
import logging
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.routers.services_reprise import reprendre_les_services
from tessera.routers.services_running import get_sonde
from tessera.services.noyau.database import init_db
from tessera.services.noyau.services_demandes import demander, lister
from tessera.services.verification.ports_de_tessera import conflit_avec_tessera, port_vise
from tessera.services.verification.process_registry import PROCESS_REGISTRY

_DORMEUR = f'"{sys.executable}" -c "import time; time.sleep(30)"'


class Sonde:
    async def ecouteurs(self) -> dict[int, int]:
        return {}

    async def processus(self) -> dict[int, object]:
        return {}


@pytest.fixture(autouse=True)
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    ws = tmp_path / "workspace"
    ws.mkdir()
    db_path = tmp_path / "tessera.db"
    asyncio.run(init_db(db_path))
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    monkeypatch.setattr(settings, "ide_db_path", db_path)
    app.dependency_overrides[get_sonde] = lambda: Sonde()
    yield ws
    asyncio.run(PROCESS_REGISTRY.tout_arreter())
    app.dependency_overrides.clear()


def _projet(ws: Path, commande: str) -> None:
    dossier = ws / "alpha"
    dossier.mkdir(exist_ok=True)
    (dossier / "CLAUDE.md").write_text("# alpha\n", encoding="utf-8")
    services = [{"nom": "web", "commande": commande}]
    (dossier / "agents.json").write_text(
        json.dumps({"project_id": "alpha", "services": services}), encoding="utf-8"
    )


def _start() -> tuple[int, str]:
    with TestClient(app) as client:
        resp = client.post("/api/v1/projects/alpha/services/start")
    return resp.status_code, resp.text


def test_explicit_frontend_port_is_refused(workspace: Path) -> None:
    _projet(workspace, f"{_DORMEUR} --port 5173")
    code, texte = _start()
    assert code == 409
    assert "5173" in texte


def test_bare_npm_run_dev_is_refused(workspace: Path) -> None:
    _projet(workspace, "npm run dev")
    code, texte = _start()
    assert code == 409
    assert "5173" in texte


def test_backend_port_is_refused(workspace: Path) -> None:
    _projet(workspace, "uvicorn app:app -p 8100")
    code, texte = _start()
    assert code == 409
    assert "8100" in texte


def test_other_port_starts(workspace: Path) -> None:
    _projet(workspace, f"{_DORMEUR} --port 5180")
    assert _start()[0] == 200


@pytest.mark.parametrize(
    ("commande", "attendu"),
    [
        ("npm run dev -- --port 5180", 5180),
        ("vite --port=4000", 4000),
        ("PORT=3000 node x.js", 3000),
        ("vite", 5173),
        ("python -m http.server", None),
    ],
)
def test_port_vise(commande: str, attendu: int | None) -> None:
    assert port_vise(commande) == attendu


def _frontend(dossier: Path, dev: str | None, vite: str | None) -> None:
    dossier.mkdir(parents=True, exist_ok=True)
    if dev is not None:
        pkg = {"scripts": {"dev": dev}}
        (dossier / "package.json").write_text(json.dumps(pkg), encoding="utf-8")
    if vite is not None:
        (dossier / "vite.config.ts").write_text(vite, encoding="utf-8")


_VITE_5194 = "export default { plugins: [a({x: 1})], server: { host: 'x', port: 5194 } }"


@pytest.mark.parametrize(
    ("dev", "vite", "attendu"),
    [
        ("vite", _VITE_5194, 5194),
        ("vite", "export default { port: 5194 }", 5173),
        ("vite", "export default { server: { open: true } }", 5173),
        ("vite", None, 5173),
        ("vite --port 5174", _VITE_5194, 5174),
        ("next dev", None, None),
        ("next dev", _VITE_5194, None),
        (None, _VITE_5194, 5173),
    ],
)
def test_port_vise_reads_the_service_folder(
    tmp_path: Path, dev: str | None, vite: str | None, attendu: int | None
) -> None:
    _frontend(tmp_path, dev, vite)
    assert port_vise("npm run dev", tmp_path) == attendu


def test_port_vise_with_bare_vite_reads_the_config(tmp_path: Path) -> None:
    _frontend(tmp_path, None, _VITE_5194)
    assert port_vise("vite", tmp_path) == 5194


def test_port_vise_with_invalid_package_json_stays_closed(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{nope", encoding="utf-8")
    assert port_vise("npm run dev", tmp_path) == 5173


def _projet_frontend(ws: Path, dev: str | None, vite: str | None) -> None:
    _projet(ws, "npm run dev")
    agents = ws / "alpha" / "agents.json"
    services = [{"nom": "web", "commande": "npm run dev", "cwd": "frontend"}]
    agents.write_text(
        json.dumps({"project_id": "alpha", "services": services}), encoding="utf-8"
    )
    _frontend(ws / "alpha" / "frontend", dev, vite)


def test_service_with_port_in_vite_config_is_not_refused(workspace: Path) -> None:
    _projet_frontend(workspace, "vite", _VITE_5194)
    dossier = workspace / "alpha" / "frontend"
    assert port_vise("npm run dev", dossier) == 5194
    assert conflit_avec_tessera("npm run dev", dossier) is None


def test_service_without_port_in_vite_config_is_refused(workspace: Path) -> None:
    _projet_frontend(workspace, "vite", "export default {}")
    code, texte = _start()
    assert code == 409
    assert "5173" in texte


def test_service_script_with_tessera_port_is_refused(workspace: Path) -> None:
    _projet_frontend(workspace, "vite --port 5174", None)
    code, texte = _start()
    assert code == 409
    assert "5174" in texte


def test_resume_does_not_relaunch_a_refused_service(
    workspace: Path, caplog: pytest.LogCaptureFixture
) -> None:
    _projet(workspace, "npm run dev")
    db = settings.ide_db_path
    asyncio.run(demander(db, "alpha"))
    with caplog.at_level(logging.WARNING):
        asyncio.run(reprendre_les_services(db, Sonde(), PROCESS_REGISTRY))
    assert PROCESS_REGISTRY.services_de("alpha") == []
    assert asyncio.run(lister(db)) == []
    assert "services_non_repris" in caplog.text
