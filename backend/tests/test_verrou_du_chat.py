"""Le chat conversationnel écrit aussi dans l'arbre — ticket-139.

ADR-019 fait du chat un producteur de travail de première classe : il écrit
sur une branche `chat-<horodatage>` et commite, comme un run le fait sur celle
de son ticket. ADR-038 annonce un verrou « partagé par tous les points
d'entrée — run unique, file, autonome, chat ».

Mais le verrou n'est pris que sur `POST /chat/run`, qui lance un pipeline. Un
**tour de chat** passe par la WebSocket et n'en prend aucun, alors que
`_commit_if_written` crée une branche dès que l'agent a écrit. Pendant qu'un
run tourne, ce `create_branch` fait un checkout sous le codeur : exactement la
panne qu'ADR-038 décrit, prise par l'autre porte.
"""
import asyncio
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.services.database import init_db
from tessera.services.run_registry import RUN_REGISTRY, RunActif


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


def _occuper(project_id: str, ticket_id: str) -> RunActif:
    """Marque le projet comme portant un run, sans en lancer un vrai."""
    run = RunActif(run_id="run-occupe", project_id=project_id, ticket_id=ticket_id)
    RUN_REGISTRY._runs[run.run_id] = run
    return run


def test_un_tour_de_chat_est_refuse_pendant_un_run(client: TestClient) -> None:
    # La panne : `_commit_if_written` crée une branche dès que l'agent a
    # écrit. Sur un projet où un run tourne, ce checkout déplace l'arbre sous
    # le codeur — ce qu'ADR-038 interdit pour deux runs, et qui passe ici.
    _occuper("mon-projet", "ticket-001")
    try:
        with client.websocket_connect(
            "/api/v1/projects/mon-projet/chat"
        ) as ws:
            ws.send_json({"conversation_id": "c1", "message": "écris un fichier"})
            reponse = ws.receive_json()
    finally:
        RUN_REGISTRY.fermer("run-occupe")

    assert reponse["type"] == "error", (
        f"le tour a démarré alors qu'un run tourne : {reponse}"
    )
    assert "ticket-001" in reponse["detail"]


def test_un_tour_de_chat_passe_sur_un_projet_libre(client: TestClient) -> None:
    # Le pendant du précédent : le refus doit tenir au run, pas au chat. Sans
    # ce test, bloquer le chat en toutes circonstances passerait le premier.
    with client.websocket_connect("/api/v1/projects/mon-projet/chat") as ws:
        ws.send_json({"conversation_id": "c1", "message": "bonjour"})
        reponse = ws.receive_json()

    assert reponse["type"] != "error" or "tourne déjà" not in reponse.get(
        "detail", ""
    )


def test_un_run_est_refuse_pendant_un_tour_de_chat(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # La réciproque, et elle compte autant : le verrou est partagé, donc le
    # chat qui écrit doit bloquer le pipeline comme le pipeline bloque le chat.
    import asyncio as _asyncio

    relache = _asyncio.Event()

    class _ServiceQuiTraine:
        async def send(self, **kwargs: object) -> object:
            await relache.wait()
            raise AssertionError("jamais atteint")

    async def _build(project_id: str) -> _ServiceQuiTraine:
        return _ServiceQuiTraine()

    monkeypatch.setattr("tessera.routers.chat._build_service", _build)

    with client.websocket_connect("/api/v1/projects/mon-projet/chat") as ws:
        ws.send_json({"conversation_id": "c1", "message": "écris"})
        assert ws.receive_json()["type"] == "start"

        refus = client.post(
            "/api/v1/orchestrator/run",
            json={"project_id": "mon-projet", "ticket_id": "ticket-001"},
        )
        assert refus.status_code == 409, refus.text
        assert "chat" in refus.json()["detail"]
        relache.set()


def test_le_verrou_est_relache_quand_le_tour_leve(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Un verrou jamais relâché bloque le projet jusqu'au redémarrage du
    # backend : c'est le `finally` de `RunRegistry.acquire` qui l'empêche.
    class _ServiceQuiCasse:
        async def send(self, **kwargs: object) -> object:
            raise RuntimeError("panne du provider")

    async def _build(project_id: str) -> _ServiceQuiCasse:
        return _ServiceQuiCasse()

    monkeypatch.setattr("tessera.routers.chat._build_service", _build)

    with client.websocket_connect("/api/v1/projects/mon-projet/chat") as ws:
        ws.send_json({"conversation_id": "c1", "message": "écris"})
        for _ in range(5):
            if ws.receive_json()["type"] == "error":
                break

    assert RUN_REGISTRY.projet_occupe("mon-projet") is False


def test_le_chat_ne_se_signale_pas_lui_meme_comme_run_en_cours(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Effet de bord du verrou : le tour le tient, donc `is_running` répond oui
    # depuis l'intérieur du tour. Sans distinction, l'UI cacherait le bouton
    # « lancer » à cause d'une occupation qui est la sienne.
    from tessera.services.chat_service import ChatReply

    class _ServiceMuet:
        async def send(self, **kwargs: object) -> ChatReply:
            return ChatReply(content="ok", cost_usd=0.0)

    async def _build(project_id: str) -> _ServiceMuet:
        return _ServiceMuet()

    monkeypatch.setattr("tessera.routers.chat._build_service", _build)

    with client.websocket_connect("/api/v1/projects/mon-projet/chat") as ws:
        ws.send_json({"conversation_id": "c1", "message": "bonjour"})
        # Deux trames exactement : un service qui n'émet aucun token ne
        # produit que `start` et `done`. En lire une de plus bloquerait le
        # test jusqu'au timeout.
        premiere = ws.receive_json()
        done = ws.receive_json()

    assert premiere["type"] == "start"
    assert done["type"] == "done", done
    assert done["run_in_progress"] is False
