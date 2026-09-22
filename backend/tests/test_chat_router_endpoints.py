"""Le tour de conversation du chat, vu du WebSocket — ticket-053.

`test_chat_router.py` couvre la lecture de l'historique. Ici c'est le chemin
WebSocket : l'ordre des trames, la persistance du message utilisateur avant
l'appel, et le plafond de conversation.
"""
import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.services.chat_service import ChatBudgetExceeded, ChatReply
from tessera.services.database import init_db, list_chat_messages


@pytest.fixture(autouse=True)
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    # Fixture *synchrone* : `init_db` tourne dans sa propre boucle, close et
    # drainée avant que celle du test n'existe. Avec une fixture `async`, le
    # thread interne d'aiosqlite survit parfois à la fermeture de la boucle du
    # test précédent, et la suite complète se termine sur un
    # « RuntimeError: Event loop is closed ».
    ws = tmp_path / "workspace"
    project = ws / "mon-projet"
    (project / "memory").mkdir(parents=True)
    (project / "CLAUDE.md").write_text("# mon-projet\n\nTest.\n", encoding="utf-8")
    for status in ("todo", "in-progress", "in-review", "done", "blocked"):
        (project / "tickets" / status).mkdir(parents=True)

    db_path = tmp_path / "tessera.db"
    asyncio.run(init_db(db_path))

    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    monkeypatch.setattr(settings, "ide_db_path", db_path)
    monkeypatch.setattr(settings, "chat_max_conversation_usd", 2.0)
    return ws


def _client() -> TestClient:
    return TestClient(app)


class _FakeChatService:
    """ChatService doublé : streame un token puis répond."""

    def __init__(self, reply: ChatReply | None = None, raises: Exception | None = None) -> None:
        self.reply = reply or ChatReply(content="Bonjour.", cost_usd=0.03)
        self.raises = raises
        self.received: list[str] = []

    async def send(self, **kwargs: object) -> ChatReply:
        self.received.append(str(kwargs["message"]))
        if self.raises is not None:
            raise self.raises
        on_token = kwargs.get("on_token")
        if on_token is not None:
            await on_token(self.reply.content)  # type: ignore[operator]
        return self.reply


def _patch_service(monkeypatch: pytest.MonkeyPatch, service: _FakeChatService) -> None:
    async def _build(project_id: str) -> _FakeChatService:
        return service

    monkeypatch.setattr("tessera.routers.chat._build_service", _build)


# ------------------------------------------------------------------
# Un tour complet
# ------------------------------------------------------------------


def test_un_tour_emet_start_puis_token_puis_done(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _FakeChatService(
        ChatReply(content="Bonjour.", cost_usd=0.03, branch="chat-20260915", commit_sha="cafe123")
    )
    _patch_service(monkeypatch, service)

    with _client().websocket_connect("/api/v1/projects/mon-projet/chat") as ws:
        ws.send_json({"conversation_id": "c1", "message": "Salut"})

        assert ws.receive_json()["type"] == "start"
        token = ws.receive_json()
        done = ws.receive_json()

    assert token == {"type": "token", "token": "Bonjour."}
    assert done["type"] == "done"
    assert done["content"] == "Bonjour."
    assert done["spent_usd"] == 0.03
    assert done["branch"] == "chat-20260915"
    assert done["commit_sha"] == "cafe123"


async def test_les_deux_tours_sont_persistes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_service(monkeypatch, _FakeChatService())

    with _client().websocket_connect("/api/v1/projects/mon-projet/chat") as ws:
        ws.send_json({"conversation_id": "c1", "message": "Salut"})
        for _ in range(3):
            ws.receive_json()

    messages = await list_chat_messages(settings.ide_db_path, "mon-projet", "c1")
    assert [(m.role, m.content) for m in messages] == [
        ("user", "Salut"),
        ("assistant", "Bonjour."),
    ]


async def test_le_message_utilisateur_survit_a_un_echec_de_l_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Il est persisté avant l'appel : si celui-ci échoue, la question reste
    # dans l'historique plutôt que de disparaître avec l'erreur.
    _patch_service(monkeypatch, _FakeChatService(raises=RuntimeError("provider indisponible")))

    with _client().websocket_connect("/api/v1/projects/mon-projet/chat") as ws:
        ws.send_json({"conversation_id": "c1", "message": "Ma question"})
        ws.receive_json()  # start
        error = ws.receive_json()

    assert error["type"] == "error"
    assert "provider indisponible" in error["detail"]

    messages = await list_chat_messages(settings.ide_db_path, "mon-projet", "c1")
    assert [(m.role, m.content) for m in messages] == [("user", "Ma question")]


# ------------------------------------------------------------------
# Refus
# ------------------------------------------------------------------


def test_message_vide_est_refuse_sans_fermer_la_connexion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _FakeChatService()
    _patch_service(monkeypatch, service)

    with _client().websocket_connect("/api/v1/projects/mon-projet/chat") as ws:
        ws.send_json({"conversation_id": "c1", "message": "   "})
        refus = ws.receive_json()

        # La connexion reste utilisable : un tour suivant doit passer.
        ws.send_json({"conversation_id": "c1", "message": "Une vraie question"})
        assert ws.receive_json()["type"] == "start"
        ws.receive_json()  # token
        ws.receive_json()  # done — drainer avant de fermer

    assert refus["type"] == "error"
    assert service.received == ["Une vraie question"]


def test_depassement_de_plafond_est_annonce_comme_tel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Un plafond atteint n'est pas une erreur technique : l'UI doit pouvoir le
    # distinguer pour proposer d'ouvrir une nouvelle conversation.
    _patch_service(monkeypatch, _FakeChatService(raises=ChatBudgetExceeded(2.0, 2.0)))

    with _client().websocket_connect("/api/v1/projects/mon-projet/chat") as ws:
        ws.send_json({"conversation_id": "c1", "message": "Encore une question"})
        ws.receive_json()  # start
        frame = ws.receive_json()

    assert frame["type"] == "budget_exceeded"
    assert "2.00" in frame["detail"]


def test_conversation_id_absent_retombe_sur_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_service(monkeypatch, _FakeChatService())

    with _client().websocket_connect("/api/v1/projects/mon-projet/chat") as ws:
        ws.send_json({"message": "Sans identifiant"})
        assert ws.receive_json()["conversation_id"] == "default"
        ws.receive_json()  # token
        ws.receive_json()  # done — drainer avant de fermer


# ------------------------------------------------------------------
# Construction du contexte et du service
# ------------------------------------------------------------------


async def test_le_contexte_du_chat_reprend_claude_md_tickets_et_adr(
    workspace: Path,
) -> None:
    # L'agent du chat doit recevoir le même contexte que ceux du pipeline :
    # sans lui, il répond sur un projet qu'il ne connaît pas.
    from tessera.routers.chat import _build_context

    project = workspace / "mon-projet"
    (project / "memory" / "decisions.md").write_text(
        "## ADR-001 — Une décision\n", encoding="utf-8"
    )
    (project / "tickets" / "todo" / "ticket-007.md").write_text(
        "---\nid: ticket-007\ntitle: \"Ouvert\"\ntype: feat\nstatus: todo\n"
        "priority: high\nagent: codeur\n---\n\n# ticket-007\n",
        encoding="utf-8",
    )

    context = await _build_context("mon-projet", project)

    assert "mon-projet" in context
    assert "ticket-007" in context
    assert "ADR-001" in context


async def test_le_contexte_du_chat_ne_garde_que_les_adr_qui_le_concernent(
    workspace: Path,
) -> None:
    # Le chat titrait sa section « Décisions d'architecture », que
    # `services/adr.py` ne reconnaît pas : il recevait le fichier entier,
    # choix de stack compris, quand chaque agent du pipeline est filtré.
    from tessera.routers.chat import _build_context

    project = workspace / "mon-projet"
    (project / "memory" / "decisions.md").write_text(
        "## ADR-001 — Un choix de stack\n\n**Portée** : architect\n"
        "**Décision** : uv.\n\n---\n\n"
        "## ADR-002 — Une contrainte\n\n**Décision** : pas de git.\n",
        encoding="utf-8",
    )

    context = await _build_context("mon-projet", project)

    assert "## Décisions récentes" in context
    assert "ADR-002" in context
    assert "ADR-001" not in context


async def test_le_service_du_chat_n_expose_aucun_outil_shell(workspace: Path) -> None:
    # Critère de ticket-048 : un agent conversationnel exécutant des commandes
    # arbitraires dans le dépôt de l'utilisateur est hors périmètre.
    from tessera.routers.chat import _CHAT_TOOLS, _build_service

    assert "Bash" not in _CHAT_TOOLS

    service = await _build_service("mon-projet")
    assert service._provider._allowed_tools == _CHAT_TOOLS


async def test_service_du_chat_sur_un_projet_inexistant_renvoie_404() -> None:
    from fastapi import HTTPException

    from tessera.routers.chat import _build_service

    with pytest.raises(HTTPException) as exc:
        await _build_service("jamais-vu")

    assert exc.value.status_code == 404


# ------------------------------------------------------------------
# Lancement de pipeline depuis le chat — ticket-055
# ------------------------------------------------------------------


def test_la_suggestion_remonte_dans_la_trame_done(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_service(
        monkeypatch,
        _FakeChatService(
            ChatReply(content="C'est prêt.", cost_usd=0.01, suggested_ticket_id="ticket-042")
        ),
    )

    with _client().websocket_connect("/api/v1/projects/mon-projet/chat") as ws:
        ws.send_json({"conversation_id": "c1", "message": "Crée un ticket"})
        ws.receive_json()  # start
        ws.receive_json()  # token
        done = ws.receive_json()

    assert done["suggested_ticket_id"] == "ticket-042"
    assert done["run_in_progress"] is False


def test_le_lancement_transmet_la_discussion_au_codeur(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Sans ce contexte, le codeur reçoit le ticket nu et tout le raisonnement
    # de la conversation est perdu.
    import asyncio

    from tessera.services.database import save_chat_message

    asyncio.run(
        save_chat_message(
            settings.ide_db_path, "mon-projet", "c1", "user", "Il faut un endpoint /health", 0.0
        )
    )

    captured: dict[str, object] = {}

    class _FakeOrchestrator:
        def __init__(self) -> None:
            self._project_context = "contexte projet"

        async def run_pipeline(self, project_id: str, ticket_id: str, on_event: object) -> object:
            captured["context"] = self._project_context
            captured["ticket_id"] = ticket_id
            from tessera.models.ticket import TicketStatus
            from tessera.services.pipeline_events import PipelineResult

            return PipelineResult(
                ticket_id=ticket_id,
                final_status=TicketStatus.done,
                rounds=1,
                approved=True,
            )

    async def _build(project_id: str) -> _FakeOrchestrator:
        return _FakeOrchestrator()

    monkeypatch.setattr("tessera.routers.orchestrator._build_orchestrator", _build)

    resp = _client().post(
        "/api/v1/projects/mon-projet/chat/run",
        json={"conversation_id": "c1", "ticket_id": "ticket-042"},
    )

    assert resp.status_code == 200
    assert resp.json()["approved"] is True
    assert "endpoint /health" in str(captured["context"])
    assert "Discussion ayant mené à ce ticket" in str(captured["context"])


def test_un_lancement_concurrent_est_refuse_avec_409(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Deux pipelines sur le même dépôt violeraient l'isolation par branche.
    from tessera.routers.chat import _RUN_LOCK

    async def _build(project_id: str) -> object:
        raise AssertionError("ne doit pas être atteint")

    monkeypatch.setattr("tessera.routers.orchestrator._build_orchestrator", _build)
    monkeypatch.setattr(_RUN_LOCK, "_running", {"mon-projet": "ticket-001"})

    resp = _client().post(
        "/api/v1/projects/mon-projet/chat/run",
        json={"conversation_id": "c1", "ticket_id": "ticket-042"},
    )

    assert resp.status_code == 409
    assert "tourne déjà" in resp.json()["detail"]
