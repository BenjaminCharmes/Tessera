"""`STATIC_TOKEN` protège toutes les routes, WebSockets comprises — ticket-120.

Panne : `StaticTokenMiddleware` héritait de `BaseHTTPMiddleware`, dont
`__call__` laisse passer tout scope non-`http` sans appeler `dispatch`. Les
trois routes `@router.websocket` — pipeline, chat, flux agents — restaient
ouvertes alors que `config.py` et `CLAUDE.md` promettaient « toutes les
requêtes ». Le même middleware, ajouté après CORS donc le plus externe,
renvoyait 401 au préflight `OPTIONS`, qu'un navigateur envoie sans en-tête.
"""
import asyncio
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from tessera.config import Settings, settings
from tessera.main import app
from tessera.services.database import init_db

_RACINE = Path(__file__).resolve().parents[2]
_TOKEN = "s3cret-de-test"


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    ws = tmp_path / "workspace"
    ws.mkdir()
    db_path = tmp_path / "tessera.db"
    asyncio.run(init_db(db_path))
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    monkeypatch.setattr(settings, "ide_db_path", db_path)
    monkeypatch.setattr(settings, "static_token", _TOKEN)
    return TestClient(app)


# ------------------------------------------------------------------
# WebSockets
# ------------------------------------------------------------------


def test_une_websocket_sans_token_est_refusee(client: TestClient) -> None:
    # Le cœur de la panne : `BaseHTTPMiddleware` ignorait ce scope.
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/api/v1/agents/stream"):
            pass

    assert exc.value.code == 4401


def test_une_websocket_avec_token_en_query_est_acceptee(client: TestClient) -> None:
    # `new WebSocket(url)` n'accepte pas d'en-tête : le navigateur ne peut
    # passer le token que dans l'URL.
    with client.websocket_connect(f"/api/v1/agents/stream?token={_TOKEN}") as ws:
        ws.close()


def test_une_websocket_avec_bearer_est_acceptee(client: TestClient) -> None:
    with client.websocket_connect(
        "/api/v1/agents/stream", headers={"Authorization": f"Bearer {_TOKEN}"}
    ) as ws:
        ws.close()


def test_une_websocket_avec_mauvais_token_est_refusee(client: TestClient) -> None:
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/api/v1/agents/stream?token=faux"):
            pass

    assert exc.value.code == 4401


# ------------------------------------------------------------------
# HTTP
# ------------------------------------------------------------------


def test_une_requete_http_sans_bearer_recoit_401(client: TestClient) -> None:
    assert client.get("/api/v1/projects").status_code == 401


def test_une_requete_http_avec_bearer_passe(client: TestClient) -> None:
    reponse = client.get(
        "/api/v1/projects", headers={"Authorization": f"Bearer {_TOKEN}"}
    )

    assert reponse.status_code == 200


def test_un_bearer_faux_recoit_401(client: TestClient) -> None:
    reponse = client.get(
        "/api/v1/projects", headers={"Authorization": "Bearer faux"}
    )

    assert reponse.status_code == 401


def test_un_preflight_options_sans_bearer_n_est_pas_refuse(client: TestClient) -> None:
    # Le navigateur envoie le préflight lui-même, sans `Authorization` : un
    # 401 ici bloque toute requête cross-origin avant qu'elle ne parte.
    reponse = client.options(
        "/api/v1/projects",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )

    assert reponse.status_code != 401


def test_health_reste_ouvert(client: TestClient) -> None:
    assert client.get("/health").status_code == 200


def test_sans_token_configure_tout_passe(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "static_token", "")

    assert client.get("/api/v1/projects").status_code == 200
    with client.websocket_connect("/api/v1/agents/stream") as ws:
        ws.close()


# ------------------------------------------------------------------
# Interface locale et documentation des variables
# ------------------------------------------------------------------


def test_le_makefile_ne_sert_pas_sur_toutes_les_interfaces() -> None:
    # L'API est ouverte par défaut : sur `0.0.0.0`, tout le réseau local y
    # accède sans token.
    makefile = (_RACINE / "Makefile").read_text(encoding="utf-8")

    assert "0.0.0.0" not in makefile


def test_env_example_mentionne_chaque_variable_de_config() -> None:
    # Une variable lue par `config.py` mais absente de `.env.example` n'existe
    # pour personne : `make setup` copie ce fichier, et c'est là qu'on cherche.
    exemple = (_RACINE / ".env.example").read_text(encoding="utf-8")
    variables = {nom.upper() for nom in Settings.model_fields}

    manquantes = sorted(v for v in variables if not re.search(rf"^#? ?{v}=", exemple, re.MULTILINE))

    assert manquantes == [], f"absentes de .env.example : {manquantes}"
