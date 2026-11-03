"""A foreign `Host` or `Origin` never reaches the API, even without a token — ticket-704.

Sans `STATIC_TOKEN`, le loopback est la seule barrière. Le CORS n'empêche
qu'une page tierce de *lire* une réponse et ne s'applique pas aux WebSocket ;
aucun contrôle ne portait sur `Host`, donc un rebond DNS suffisait à piloter
l'API. Le client de test s'adresse à `testserver`, admis par `conftest.py` ;
chaque test ci-dessous fixe sa propre liste quand elle compte.
"""
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from tessera.auth import _host_without_port, _is_allowed_origin
from tessera.config import settings
from tessera.main import app

_OBSERVE = "/api/v1/orchestrator/observe"
# `websocket_connect` vise toujours `testserver`, quel que soit `base_url` : le
# `Host` loopback se pose à la main, sinon le refus viendrait du `Host`.
_LOCAL = {"Host": "localhost"}
# Un « localhost:5173 » en identifiant devant un vrai hôte étranger. Le `@` est
# posé à part : un littéral de ce genre ressemble à une adresse e-mail et le
# contrôle des traces professionnelles du dépôt le refuserait.
_USERINFO_TROMPEUR = "http://localhost:5173" + chr(64) + "evil.example"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(settings, "static_token", "")
    monkeypatch.setattr(settings, "allowed_hosts", "")
    return TestClient(app, base_url="http://localhost")


def test_foreign_host_is_refused(client: TestClient) -> None:
    reponse = client.get("/api/v1/projects", headers={"Host": "evil.example"})

    assert reponse.status_code == 403


def test_foreign_host_with_port_is_refused(client: TestClient) -> None:
    reponse = client.get("/api/v1/projects", headers={"Host": "evil.example:8000"})

    assert reponse.status_code == 403


def test_foreign_host_websocket_is_closed(client: TestClient) -> None:
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(_OBSERVE, headers={"Host": "evil.example"}):
            pass

    assert exc.value.code == 4403


@pytest.mark.parametrize("host", ["localhost", "localhost:8000", "127.0.0.1:8100", "[::1]:8000"])
def test_loopback_host_passes(client: TestClient, host: str) -> None:
    reponse = client.get("/api/v1/projects", headers={"Host": host})

    assert reponse.status_code == 200


def test_declared_host_passes(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "allowed_hosts", "tessera.lan, Poste.Local")

    for host in ("tessera.lan:8000", "poste.local"):
        reponse = client.get("/api/v1/projects", headers={"Host": host})
        assert reponse.status_code == 200
    assert client.get("/api/v1/projects", headers={"Host": "evil.example"}).status_code == 403


def test_foreign_origin_http_is_refused(client: TestClient) -> None:
    reponse = client.get("/api/v1/projects", headers={"Origin": "https://evil.example"})

    assert reponse.status_code == 403


def test_foreign_origin_websocket_is_closed(client: TestClient) -> None:
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(_OBSERVE, headers={**_LOCAL, "Origin": "https://evil.example"}):
            pass

    assert exc.value.code == 4403


def test_foreign_origin_is_refused_before_the_token(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "static_token", "s3cret")

    reponse = client.get(
        "/api/v1/projects",
        headers={"Origin": "https://evil.example", "Authorization": "Bearer s3cret"},
    )

    assert reponse.status_code == 403


@pytest.mark.parametrize(
    "origin",
    [
        "http://localhost:5173",
        "http://localhost:5175",
        "http://127.0.0.1:5174",
        "http://tauri.localhost",
        "https://tauri.localhost",
        "tauri://localhost",
    ],
)
def test_listed_origin_passes(client: TestClient, origin: str) -> None:
    assert client.get("/api/v1/projects", headers={"Origin": origin}).status_code == 200


def test_listed_origin_and_missing_origin_pass(client: TestClient) -> None:
    for origin in ("http://localhost:5173", "http://localhost:5175", "http://tauri.localhost"):
        assert client.get("/api/v1/projects", headers={"Origin": origin}).status_code == 200
    assert client.get("/api/v1/projects").status_code == 200
    with client.websocket_connect(_OBSERVE, headers={**_LOCAL, "Origin": "http://localhost:5173"}) as ws:
        ws.close()


def test_health_stays_open(client: TestClient) -> None:
    reponse = client.get("/health", headers={"Host": "evil.example"})

    assert reponse.status_code == 200


@pytest.mark.parametrize(
    "origin",
    [
        "null",
        "http://localhost.evil.example",
        _USERINFO_TROMPEUR,
        "https://localhost:5173",
        "http://localhost:abc",
        "http://localhost:5173/chemin",
        "ftp://localhost",
        "",
    ],
)
def test_lookalike_origin_is_refused(origin: str) -> None:
    assert _is_allowed_origin(origin) is False


@pytest.mark.parametrize(
    ("brut", "attendu"),
    [
        ("Localhost:8000", "localhost"),
        ("127.0.0.1", "127.0.0.1"),
        ("[::1]:8000", "[::1]"),
        ("[::1]", "[::1]"),
        ("", ""),
    ],
)
def test_host_without_port(brut: str, attendu: str) -> None:
    assert _host_without_port(brut) == attendu
