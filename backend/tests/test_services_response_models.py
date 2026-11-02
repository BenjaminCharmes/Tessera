"""Response models of the services routes — ticket-679."""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.services.process_registry import PROCESS_REGISTRY, Service
from tessera.services.service_etat import (
    ServiceEtat,
    ServicesArretes,
    ServicesDemarres,
)

_BASE = "/api/v1/projects/mon-projet/services"
_API_TS = Path(__file__).resolve().parents[2] / "frontend/src/types/api.ts"


class _FakeProcess:
    """Stand-in for an asyncio subprocess: only `returncode` is read."""

    def __init__(self, returncode: int | None) -> None:
        self.returncode = returncode


@pytest.fixture(autouse=True)
def _workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workspace = tmp_path / "workspace"
    (workspace / "mon-projet").mkdir(parents=True)
    monkeypatch.setattr(settings, "ide_workspace_dir", workspace)
    monkeypatch.setattr(PROCESS_REGISTRY, "_services", {})


def _service() -> Service:
    return Service(
        nom="web",
        project_id="mon-projet",
        pid=4242,
        processus=_FakeProcess(None),
        demarre_a=datetime(2026, 10, 30, 8, 0, 0, tzinfo=timezone.utc),
        sortie=["ready on http://localhost:5175/"],
    )


def _interface_keys(interface: str) -> set[str]:
    source = _API_TS.read_text(encoding="utf-8")
    body = source.split(f"export interface {interface} {{", 1)[1].split("\n}", 1)[0]
    return set(re.findall(r"^  (\w+)\??:", body, flags=re.MULTILINE))


def test_model_keys_match_the_front_interface() -> None:
    assert set(ServiceEtat.model_fields) == _interface_keys("ServiceActif")


def test_list_route_json_is_unchanged_byte_for_byte() -> None:
    PROCESS_REGISTRY._services = {"mon-projet": [_service()]}

    resp = TestClient(app).get(_BASE)

    expected = (
        b'[{"nom":"web","project_id":"mon-projet","pid":4242,'
        b'"demarre_a":"2026-10-30T08:00:00+00:00","en_cours":true,'
        b'"code_de_sortie":null,"sortie":["ready on http://localhost:5175/"],'
        b'"arrete_a_la_main":false}]'
    )
    assert resp.status_code == 200
    assert resp.content == expected


def test_etat_follows_the_process_state() -> None:
    assert _service().etat().code_de_sortie is None
    stopped = Service(nom="web", project_id="p", processus=_FakeProcess(3))
    assert stopped.etat().code_de_sortie == 3
    assert Service(nom="web", project_id="p").etat().code_de_sortie is None

    snapshot = PROCESS_REGISTRY.instantane()
    assert snapshot == []


def test_snapshot_keeps_the_model_key_order() -> None:
    PROCESS_REGISTRY._services = {"mon-projet": [_service()]}

    assert [list(item) for item in PROCESS_REGISTRY.instantane()] == [
        list(ServiceEtat.model_fields)
    ]


def test_stop_route_json_is_unchanged_byte_for_byte() -> None:
    resp = TestClient(app).post(f"{_BASE}/stop")

    assert resp.status_code == 200
    assert resp.content == b'{"arretes":0}'


def test_start_response_model_wraps_the_states() -> None:
    body = ServicesDemarres(services=[_service().etat()])

    assert json.loads(body.model_dump_json()) == {
        "services": [_service().etat().model_dump()]
    }
    assert ServicesArretes(arretes=2).model_dump() == {"arretes": 2}


def test_routes_declare_their_response_models() -> None:
    paths = app.openapi()["paths"]
    prefix = "/api/v1/projects/{project_id}/services"

    def schema(path: str, method: str) -> dict[str, object]:
        content = paths[path][method]["responses"]["200"]["content"]
        found: dict[str, object] = content["application/json"]["schema"]
        return found

    assert schema(f"{prefix}/start", "post") == {
        "$ref": "#/components/schemas/ServicesDemarres"
    }
    assert schema(f"{prefix}/stop", "post") == {
        "$ref": "#/components/schemas/ServicesArretes"
    }
    listed = schema(prefix, "get")
    assert listed["items"] == {"$ref": "#/components/schemas/ServiceEtat"}
