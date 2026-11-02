"""A queue is followed by the id the launch returned — ticket-431."""
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.models.ticket import TicketStatus
from tessera.services.database import create_run, finish_run, save_event
from tessera.services.pipeline_events import EventType, OrchestratorEvent, PipelineResult
from tessera.services.run_executor import _suivre
from tessera.services.run_registry import RUN_REGISTRY
from tessera.services.run_status import statut_d_un_run_termine

_TS = "2026-10-14T10:00:00+00:00"


class _FileDoublee:
    """Orchestrateur doublé : joue chaque ticket comme le fait `run_queue`."""

    async def run_queue(
        self,
        project_id: str,
        ticket_ids: list[str],
        on_event: object,
        dialogue: object = None,
        envelope_run_id: str | None = None,
        budget_override_usd: float | None = None,
    ) -> list[PipelineResult]:
        resultats: list[PipelineResult] = []
        for index, ticket_id in enumerate(ticket_ids, start=1):
            await on_event(  # type: ignore[operator]
                OrchestratorEvent(
                    type=EventType.QUEUE_PROGRESS,
                    ticket_id=ticket_id,
                    data={
                        "index": index,
                        "total": len(ticket_ids),
                        "restants": ticket_ids[index:],
                        "faits": ticket_ids[: index - 1],
                    },
                )
            )
            enfant = await create_run(
                settings.ide_db_path, project_id, ticket_id,
                parent_run_id=envelope_run_id,
            )
            await finish_run(
                settings.ide_db_path, enfant, rounds=1, approved=True, final_status="done"
            )
            resultats.append(
                PipelineResult(
                    ticket_id=ticket_id, final_status=TicketStatus.done,
                    rounds=1, approved=True,
                )
            )
        return resultats


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    projet = tmp_path / "workspace" / "projet-file"
    projet.mkdir(parents=True)
    (projet / "CLAUDE.md").write_text("# projet-file\n", encoding="utf-8")
    monkeypatch.setattr(settings, "ide_workspace_dir", tmp_path / "workspace")

    async def _build(project_id: str) -> _FileDoublee:
        return _FileDoublee()

    monkeypatch.setattr("tessera.routers.orchestrator.build_orchestrator", _build)
    with TestClient(app) as c:
        yield c


def _lancer_la_file(client: TestClient) -> str:
    """Launch a three-ticket queue and wait for `run_closed`."""
    with client.websocket_connect("/api/v1/orchestrator/observe") as ws:
        reponse = client.post(
            "/api/v1/orchestrator/run",
            json={
                "project_id": "projet-file", "mode": "queue",
                "ticket_ids": ["ticket-001", "ticket-002", "ticket-003"],
            },
        )
        assert reponse.status_code == 202, reponse.text
        for _ in range(60):
            if ws.receive_json().get("type") == "run_closed":
                break
    return str(reponse.json()["run_id"])


def test_events_answer_to_the_id_a_queue_launch_returned(client: TestClient) -> None:
    run_id = _lancer_la_file(client)

    reponse = client.get(f"/api/v1/runs/{run_id}/events")

    assert reponse.status_code == 200
    types = [e["type"] for e in reponse.json()]
    assert types.count("queue_progress") == 3


def test_status_of_a_finished_queue_lists_the_tickets_it_played(
    client: TestClient,
) -> None:
    run_id = _lancer_la_file(client)

    corps = client.get(f"/api/v1/runs/{run_id}").json()

    assert corps["statut"] == "terminé"
    assert corps["mode"] == "queue"
    assert corps["project_id"] == "projet-file"
    assert corps["approuves"] == ["ticket-001", "ticket-002", "ticket-003"]
    assert corps["arretes"] == []
    assert corps["faits"] == corps["approuves"]
    assert corps["restants"] == []
    assert corps["fin"] is not None


def test_status_of_a_live_queue_gives_current_done_and_left() -> None:
    run = RUN_REGISTRY.ouvrir("projet-vivant", "ticket-001", mode="queue")
    try:
        _suivre(run, OrchestratorEvent(
            type=EventType.QUEUE_PROGRESS, ticket_id="ticket-002",
            data={
                "index": 2, "total": 4,
                "faits": ["ticket-001"], "restants": ["ticket-003", "ticket-004"],
            },
        ))
        reponse = TestClient(app).get(f"/api/v1/runs/{run.run_id}")
    finally:
        RUN_REGISTRY.fermer(run.run_id)

    corps = reponse.json()
    assert corps["statut"] == "en cours"
    assert corps["ticket_courant"] == "ticket-002"
    assert corps["approuves"] == ["ticket-001"]
    assert corps["arretes"] == []
    assert corps["faits"] == ["ticket-001"]
    assert corps["restants"] == ["ticket-003", "ticket-004"]
    assert corps["fin"] is None


async def test_status_of_a_queue_stopped_early_is_interrupted() -> None:
    db = settings.ide_db_path
    enveloppe = await create_run(db, "projet-file", "queue", mode="queue")
    enfant = await create_run(db, "projet-file", "ticket-001", parent_run_id=enveloppe)
    await finish_run(db, enfant, rounds=1, approved=True, final_status="done")
    await save_event(
        db, enveloppe, "queue_progress", None,
        {"index": 1, "restants": ["ticket-002"], "faits": []}, _TS,
        ticket_id="ticket-001",
    )
    await finish_run(db, enveloppe, rounds=1, approved=False, final_status="todo")

    corps = TestClient(app).get(f"/api/v1/runs/{enveloppe}").json()

    assert corps["statut"] == "interrompu"
    assert corps["approuves"] == ["ticket-001"]
    assert corps["restants"] == ["ticket-002"]


async def test_status_of_a_run_without_end_that_left_the_registry_is_in_progress() -> None:
    enveloppe = await create_run(settings.ide_db_path, "projet-file", "queue", mode="queue")

    corps = TestClient(app).get(f"/api/v1/runs/{enveloppe}").json()

    assert corps["statut"] == "en cours"


def test_status_of_an_unknown_run_is_404() -> None:
    assert TestClient(app).get("/api/v1/runs/pas-un-run").status_code == 404


@pytest.mark.parametrize(
    ("final_status", "restants", "attendu"),
    [
        ("done", [], "terminé"),
        ("done", ["ticket-002"], "interrompu"),
        ("todo", ["ticket-002"], "interrompu"),
        ("blocked", [], "interrompu"),
        ("interrupted", [], "interrompu"),
        (None, [], "terminé"),
    ],
)
def test_finished_status_mapping(
    final_status: str | None, restants: list[str], attendu: str
) -> None:
    assert statut_d_un_run_termine(final_status, restants) == attendu


async def test_create_run_keeps_the_id_it_is_given_and_draws_one_otherwise() -> None:
    db = settings.ide_db_path

    assert await create_run(db, "projet-file", "ticket-001", run_id="id-choisi") == "id-choisi"
    assert len(await create_run(db, "projet-file", "ticket-002")) == 36
