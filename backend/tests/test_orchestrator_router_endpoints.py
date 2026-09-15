"""Endpoints du router orchestrateur — ticket-053."""
import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vibe_ide.config import settings
from vibe_ide.main import app
from vibe_ide.models.ticket import TicketStatus
from vibe_ide.services.database import init_db
from vibe_ide.services.pipeline_events import EventType, OrchestratorEvent, PipelineResult


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
    (project / "tickets" / "todo" / "ticket-001.md").write_text(
        "---\n"
        "id: ticket-001\n"
        'title: "Un ticket"\n'
        "type: feat\n"
        "status: todo\n"
        "priority: medium\n"
        "agent: codeur\n"
        "---\n\n# ticket-001\n",
        encoding="utf-8",
    )

    db_path = tmp_path / "vibe.db"
    asyncio.run(init_db(db_path))

    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    monkeypatch.setattr(settings, "ide_db_path", db_path)
    monkeypatch.setattr(settings, "llm_provider", "agent_sdk")
    return ws


def _client() -> TestClient:
    return TestClient(app)


def _approved(ticket_id: str = "ticket-001") -> PipelineResult:
    return PipelineResult(
        ticket_id=ticket_id,
        final_status=TicketStatus.done,
        rounds=1,
        approved=True,
        branch=f"{ticket_id}-slug",
        commit_sha="abc1234",
    )


class _FakeOrchestrator:
    """Orchestrateur doublé : émet quelques événements puis approuve."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def run_pipeline(
        self, project_id: str, ticket_id: str, on_event: object, run_id: str | None = None
    ) -> PipelineResult:
        self.calls.append((project_id, ticket_id))
        await on_event(  # type: ignore[operator]
            OrchestratorEvent(type=EventType.BRANCH_CREATED, ticket_id=ticket_id,
                              data={"branch": f"{ticket_id}-slug"})
        )
        await on_event(  # type: ignore[operator]
            OrchestratorEvent(type=EventType.PIPELINE_DONE, ticket_id=ticket_id,
                              data={"approved": True, "rounds": 1})
        )
        return _approved(ticket_id)

    async def run_autonomous(
        self, project_id: str, max_tickets: int = 5, on_event: object = None
    ) -> list[PipelineResult]:
        self.calls.append((project_id, f"autonomous:{max_tickets}"))
        if on_event is not None:
            # Le vrai orchestrateur relaie ses événements : les émettre permet
            # au test de se synchroniser sur la fin du traitement au lieu de
            # fermer la socket en plein vol.
            await on_event(  # type: ignore[operator]
                OrchestratorEvent(type=EventType.PIPELINE_DONE, ticket_id="ticket-001",
                                  data={"approved": True, "rounds": 1})
            )
        return [_approved()]


# ------------------------------------------------------------------
# POST /orchestrator/run
# ------------------------------------------------------------------


def test_run_sur_un_projet_inexistant_renvoie_404() -> None:
    resp = _client().post(
        "/api/v1/orchestrator/run",
        json={"project_id": "jamais-vu", "ticket_id": "ticket-001"},
    )
    assert resp.status_code == 404


def test_run_sans_ticket_id_est_refuse() -> None:
    resp = _client().post("/api/v1/orchestrator/run", json={"project_id": "mon-projet"})
    assert resp.status_code == 422


def test_run_renvoie_le_resultat_du_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeOrchestrator()

    async def _build(project_id: str) -> _FakeOrchestrator:
        return fake

    monkeypatch.setattr("vibe_ide.routers.orchestrator._build_orchestrator", _build)

    resp = _client().post(
        "/api/v1/orchestrator/run",
        json={"project_id": "mon-projet", "ticket_id": "ticket-001"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["approved"] is True
    assert body["branch"] == "ticket-001-slug"
    assert body["commit_sha"] == "abc1234"
    assert fake.calls == [("mon-projet", "ticket-001")]


# ------------------------------------------------------------------
# POST /orchestrator/run-autonomous
# ------------------------------------------------------------------


def test_run_autonome_transmet_max_tickets(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeOrchestrator()

    async def _build(project_id: str) -> _FakeOrchestrator:
        return fake

    monkeypatch.setattr("vibe_ide.routers.orchestrator._build_orchestrator", _build)

    resp = _client().post(
        "/api/v1/orchestrator/run-autonomous",
        json={"project_id": "mon-projet", "max_tickets": 3},
    )

    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert fake.calls == [("mon-projet", "autonomous:3")]


# ------------------------------------------------------------------
# WS /orchestrator/stream/{project_id}
# ------------------------------------------------------------------


def test_stream_sans_ticket_ni_mode_renvoie_une_erreur_explicite() -> None:
    with _client().websocket_connect("/api/v1/orchestrator/stream/mon-projet") as ws:
        ws.send_json({})
        assert "ticket_id" in ws.receive_json()["error"]


def test_stream_diffuse_les_evenements_du_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeOrchestrator()

    async def _build(project_id: str) -> _FakeOrchestrator:
        return fake

    monkeypatch.setattr("vibe_ide.routers.orchestrator._build_orchestrator", _build)

    with _client().websocket_connect("/api/v1/orchestrator/stream/mon-projet") as ws:
        ws.send_json({"ticket_id": "ticket-001"})

        first = ws.receive_json()
        second = ws.receive_json()

    assert first["type"] == "branch_created"
    assert second["type"] == "pipeline_done"
    assert second["data"]["approved"] is True


def test_stream_en_mode_autonome(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeOrchestrator()

    async def _build(project_id: str) -> _FakeOrchestrator:
        return fake

    monkeypatch.setattr("vibe_ide.routers.orchestrator._build_orchestrator", _build)

    with _client().websocket_connect("/api/v1/orchestrator/stream/mon-projet") as ws:
        ws.send_json({"mode": "autonomous", "max_tickets": 2})
        assert ws.receive_json()["type"] == "pipeline_done"

    assert fake.calls == [("mon-projet", "autonomous:2")]
