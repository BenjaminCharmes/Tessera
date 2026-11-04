"""The observation socket only trusts declared origins — ticket-754.

Tessera sert sur le loopback des apps écrites par ses agents : une page de
`localhost:61234` ne doit ni observer les runs ni répondre à un agent.
"""
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from tessera.auth import _declared_origins, _is_declared_origin
from tessera.config import settings
from tessera.main import app

_OBSERVE = "/api/v1/orchestrator/observe"
_LOCAL = {"Host": "localhost"}


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(settings, "static_token", "")
    monkeypatch.setattr(settings, "allowed_hosts", "")
    monkeypatch.setattr(settings, "allowed_origins", "")
    return TestClient(app, base_url="http://localhost")


def _connect(client: TestClient, origin: str) -> None:
    with client.websocket_connect(_OBSERVE, headers={**_LOCAL, "Origin": origin}) as ws:
        ws.close()


@pytest.mark.parametrize(
    "origin", ["http://localhost:61234", "http://127.0.0.1:8025", "http://localhost:5177"]
)
def test_undeclared_loopback_origin_websocket_is_closed(client: TestClient, origin: str) -> None:
    with pytest.raises(WebSocketDisconnect) as exc:
        _connect(client, origin)

    assert exc.value.code == 4403


@pytest.mark.parametrize(
    "origin",
    [
        "http://localhost:5173",
        "http://127.0.0.1:5176",
        "tauri://localhost",
        "http://tauri.localhost",
        "https://tauri.localhost",
    ],
)
def test_default_origin_websocket_is_admitted(client: TestClient, origin: str) -> None:
    _connect(client, origin)


def test_origin_added_by_setting_is_admitted(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "allowed_origins", "http://localhost:61234, http://Tessera.lan:5173/")

    _connect(client, "http://localhost:61234")
    _connect(client, "http://tessera.lan:5173")
    with pytest.raises(WebSocketDisconnect) as exc:
        _connect(client, "http://localhost:61235")
    assert exc.value.code == 4403


def test_missing_origin_websocket_still_passes(client: TestClient) -> None:
    with client.websocket_connect(_OBSERVE, headers=_LOCAL) as ws:
        ws.close()


def test_http_keeps_the_loopback_rule(client: TestClient) -> None:
    reponse = client.get("/api/v1/projects", headers={"Origin": "http://localhost:61234"})

    assert reponse.status_code == 200


def test_declared_origins_cover_the_default_range(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "allowed_origins", "")

    origines = _declared_origins()

    assert {"http://localhost:5173", "http://127.0.0.1:5176"} <= origines
    assert _is_declared_origin(" HTTP://LOCALHOST:5174 ") is True
    assert _is_declared_origin("http://localhost:5199") is False
    assert _is_declared_origin("") is False
