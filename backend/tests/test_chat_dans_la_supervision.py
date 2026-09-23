"""Le chat apparaît dans la supervision — ticket-130.

ADR-019 fait du chat un producteur de travail de première classe : il écrit
sur une branche et commite, comme un run. Il était pourtant le seul à
n'apparaître nulle part dans la vue qui dit ce que l'IDE est en train de
faire.

Depuis ticket-139 il tient `RUN_LOCK`, donc il entre déjà dans
`RunRegistry` — mais étiqueté comme un run ordinaire, avec un ticket nommé
« chat ». Ce fichier verrouille ce qui l'en distingue : son mode, et le fait
que sa sortie passe par le même canal que le reste.
"""
import asyncio
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.services.chat_service import ChatReply
from tessera.services.database import init_db
from tessera.services.event_hub import EVENT_HUB
from tessera.services.pipeline_events import EventType
from tessera.services.run_registry import RUN_REGISTRY


@pytest.fixture(autouse=True)
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ws = tmp_path / "workspace"
    project = ws / "mon-projet"
    (project / "memory").mkdir(parents=True)
    (project / "CLAUDE.md").write_text("# mon-projet\n", encoding="utf-8")
    for status in ("todo", "in-progress", "in-review", "done", "blocked"):
        (project / "tickets" / status).mkdir(parents=True)
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


class _ServiceQuiParle:
    """Émet un token, puis répond — le minimum pour observer un tour."""

    async def send(self, **kwargs: object) -> ChatReply:
        on_token = kwargs.get("on_token")
        if on_token is not None:
            await on_token("salut")  # type: ignore[operator]
        return ChatReply(content="salut", cost_usd=0.0)


def _brancher(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _build(project_id: str) -> _ServiceQuiParle:
        return _ServiceQuiParle()

    monkeypatch.setattr("tessera.routers.chat._build_service", _build)


# On s'abonne au hub plutôt que d'ouvrir `/observe` : une socket de test
# attend indéfiniment quand l'événement espéré n'arrive pas, si bien qu'un
# test rouge *bloque* au lieu d'échouer. L'abonnement se vide, lui, tout de
# suite.


def test_un_tour_de_chat_est_enregistre_avec_son_propre_mode(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Sans mode distinct, la carte affiche un run de ticket « chat » : le
    # chrono, les tours et le verdict d'un pipeline pour quelque chose qui
    # n'en a aucun.
    _brancher(monkeypatch)
    vus: list[dict] = []

    with client.websocket_connect("/api/v1/projects/mon-projet/chat") as chat:
        chat.send_json({"conversation_id": "c1", "message": "bonjour"})
        chat.receive_json()  # start
        vus = RUN_REGISTRY.instantane()
        for _ in range(5):
            if chat.receive_json().get("type") == "done":
                break

    modes = [run["mode"] for run in vus if run["project_id"] == "mon-projet"]
    assert modes == ["chat"], f"instantané : {vus}"


def test_le_chat_publie_sur_le_canal_d_observation(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Le canal porte « ce que l'IDE est en train de faire ». Un chat qui écrit
    # dans un dépôt sans y apparaître est précisément ce qu'ADR-019 refuse de
    # traiter comme un outil de seconde classe.
    _brancher(monkeypatch)
    abonne = EVENT_HUB.subscribe()

    try:
        with client.websocket_connect("/api/v1/projects/mon-projet/chat") as chat:
            chat.send_json({"conversation_id": "c1", "message": "bonjour"})
            for _ in range(5):
                if chat.receive_json().get("type") == "done":
                    break
        recus = abonne.vider()
    finally:
        abonne.fermer()

    types = [e.type for e in recus]
    assert EventType.AGENT_STARTED in types, f"reçus : {types}"
    assert EventType.RUN_CLOSED in types, f"reçus : {types}"
    assert all(e.project_id == "mon-projet" for e in recus)


def test_le_tour_sort_du_registre_a_la_fin(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Une entrée qui reste occupe le projet : le run suivant serait refusé
    # pour un chat terminé depuis longtemps.
    _brancher(monkeypatch)

    with client.websocket_connect("/api/v1/projects/mon-projet/chat") as chat:
        chat.send_json({"conversation_id": "c1", "message": "bonjour"})
        for _ in range(5):
            if chat.receive_json().get("type") == "done":
                break

    assert RUN_REGISTRY.projet_occupe("mon-projet") is False
