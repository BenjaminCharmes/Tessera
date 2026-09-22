"""Un run a la fois par projet, sur tous les points d'entree — ticket-121.

`RunLock` n'existait que pour `/chat/run`. Deux `POST /orchestrator/run` sur
le meme projet passaient `ensure_clean_tree`, puis le second `create_branch`
faisait un checkout sous le premier codeur.
"""
import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.models.ticket import TicketStatus
from tessera.services.database import init_db
from tessera.services.pipeline_events import EventType, OrchestratorEvent, PipelineResult
from tessera.services.run_lock import RUN_LOCK, RunAlreadyInProgress, RunLock


# ------------------------------------------------------------------
# Le verrou lui-meme
# ------------------------------------------------------------------


async def test_le_refus_nomme_le_ticket_en_cours() -> None:
    # Celui qui clique deux fois veut savoir ce qui tourne, pas seulement
    # qu'on lui dit non.
    lock = RunLock()
    async with lock.acquire("mon-projet", "ticket-007"):
        with pytest.raises(RunAlreadyInProgress) as exc:
            async with lock.acquire("mon-projet", "ticket-008"):
                pass
    assert "ticket-007" in str(exc.value)
    assert exc.value.ticket_id == "ticket-007"
    assert lock.ticket_en_cours("mon-projet") is None


async def test_le_verrou_est_partage_entre_les_routeurs() -> None:
    # Un verrou par module serait deux verrous : le chat et l'orchestrateur
    # doivent voir le meme etat.
    from tessera.routers import chat, orchestrator

    assert chat._RUN_LOCK is RUN_LOCK
    assert orchestrator._RUN_LOCK is RUN_LOCK


# ------------------------------------------------------------------
# Les endpoints
# ------------------------------------------------------------------


@pytest.fixture(autouse=True)
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ws = tmp_path / "workspace"
    for project_id in ("mon-projet", "autre-projet"):
        project = ws / project_id
        (project / "memory").mkdir(parents=True)
        (project / "CLAUDE.md").write_text(f"# {project_id}\n", encoding="utf-8")
        for status in ("todo", "in-progress", "in-review", "done", "blocked"):
            (project / "tickets" / status).mkdir(parents=True)
    db_path = tmp_path / "tessera.db"
    asyncio.run(init_db(db_path))
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    monkeypatch.setattr(settings, "ide_db_path", db_path)
    monkeypatch.setattr(settings, "llm_provider", "agent_sdk")
    return ws


def _approved(ticket_id: str) -> PipelineResult:
    return PipelineResult(
        ticket_id=ticket_id, final_status=TicketStatus.done, rounds=1, approved=True,
    )


class _OrchestrateurQuiAttend:
    """Se suspend sur une question : le run reste « en cours » tant qu'on ne repond pas."""

    async def run_pipeline(
        self,
        project_id: str,
        ticket_id: str,
        on_event: object,
        run_id: str | None = None,
        dialogue: object = None,
    ) -> PipelineResult:
        if dialogue is not None:
            await dialogue.ask("on continue ?")  # type: ignore[attr-defined]
        await on_event(  # type: ignore[operator]
            OrchestratorEvent(type=EventType.PIPELINE_DONE, ticket_id=ticket_id,
                              data={"approved": True, "rounds": 1})
        )
        return _approved(ticket_id)

    async def run_autonomous(
        self, project_id: str, max_tickets: int = 5, on_event: object = None
    ) -> list[PipelineResult]:
        return [_approved("ticket-001")]


def _brancher(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _build(project_id: str) -> _OrchestrateurQuiAttend:
        return _OrchestrateurQuiAttend()

    monkeypatch.setattr("tessera.routers.orchestrator._build_orchestrator", _build)


def test_un_second_run_sur_le_meme_projet_recoit_409(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _brancher(monkeypatch)
    client = TestClient(app)

    with client.websocket_connect("/api/v1/orchestrator/stream/mon-projet") as ws:
        ws.send_json({"ticket_id": "ticket-001"})
        assert ws.receive_json()["type"] == "agent_question"

        resp = client.post(
            "/api/v1/orchestrator/run",
            json={"project_id": "mon-projet", "ticket_id": "ticket-002"},
        )
        assert resp.status_code == 409
        assert "ticket-001" in resp.json()["detail"]

        resp = client.post(
            "/api/v1/orchestrator/run-autonomous",
            json={"project_id": "mon-projet", "max_tickets": 1},
        )
        assert resp.status_code == 409

        ws.send_json({"type": "answer", "text": "oui"})
        assert ws.receive_json()["type"] == "pipeline_done"

    # Le run fini, le projet est de nouveau libre.
    assert RUN_LOCK.ticket_en_cours("mon-projet") is None


def test_deux_projets_differents_tournent_ensemble(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _brancher(monkeypatch)
    client = TestClient(app)

    with client.websocket_connect("/api/v1/orchestrator/stream/mon-projet") as ws:
        ws.send_json({"ticket_id": "ticket-001"})
        assert ws.receive_json()["type"] == "agent_question"

        resp = client.post(
            "/api/v1/orchestrator/run",
            json={"project_id": "autre-projet", "ticket_id": "ticket-009"},
        )
        assert resp.status_code == 200
        assert resp.json()["ticket_id"] == "ticket-009"

        ws.send_json({"type": "answer", "text": "oui"})
        assert ws.receive_json()["type"] == "pipeline_done"


def test_un_second_stream_sur_le_meme_projet_recoit_une_erreur(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # La WebSocket est le chemin que l'UI emprunte : c'est la qu'un double
    # clic arrive vraiment.
    _brancher(monkeypatch)
    client = TestClient(app)

    with client.websocket_connect("/api/v1/orchestrator/stream/mon-projet") as ws:
        ws.send_json({"ticket_id": "ticket-001"})
        assert ws.receive_json()["type"] == "agent_question"

        with client.websocket_connect("/api/v1/orchestrator/stream/mon-projet") as ws2:
            ws2.send_json({"ticket_id": "ticket-002"})
            refus = ws2.receive_json()
        assert "ticket-001" in refus["error"]

        ws.send_json({"type": "answer", "text": "oui"})
        assert ws.receive_json()["type"] == "pipeline_done"
