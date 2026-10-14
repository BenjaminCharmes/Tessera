"""A queue's status tells approved tickets from stopped ones — ticket-444."""
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.services.database import (
    CAUSE_RUN_ORPHELIN,
    create_run,
    finish_run,
    save_event,
    solder_les_runs_orphelins,
)

_TS = "2026-10-14T10:00:00+00:00"
_PROJET = "projet-file"


async def _file(restants: list[str]) -> str:
    """A finished queue envelope announcing `restants` as still waiting."""
    db = settings.ide_db_path
    enveloppe = await create_run(db, _PROJET, "queue", mode="queue")
    await save_event(
        db, enveloppe, "queue_progress", None,
        {"index": 1, "restants": restants, "faits": []}, _TS,
    )
    await finish_run(db, enveloppe, rounds=1, approved=False, final_status="blocked")
    return enveloppe


async def _enfant(
    enveloppe: str, ticket: str, approved: bool, final_status: str, arret: str | None = None
) -> None:
    db = settings.ide_db_path
    run_id = await create_run(db, _PROJET, ticket, parent_run_id=enveloppe)
    await finish_run(db, run_id, 1, approved, final_status, arret)


def _statut(run_id: str) -> dict[str, object]:
    reponse = TestClient(app).get(f"/api/v1/runs/{run_id}")
    assert reponse.status_code == 200
    corps: dict[str, object] = reponse.json()
    return corps


async def test_an_approved_ticket_and_a_blocked_one_are_told_apart() -> None:
    enveloppe = await _file([])
    await _enfant(enveloppe, "ticket-070", True, "done")
    await _enfant(enveloppe, "ticket-071", False, "blocked", "testeur: délai dépassé deux fois")

    corps = _statut(enveloppe)

    assert corps["approuves"] == ["ticket-070"]
    assert corps["arretes"] == [
        {"ticket_id": "ticket-071", "motif": "testeur: délai dépassé deux fois"}
    ]
    assert corps["restants"] == []
    assert corps["statut"] == "interrompu"


async def test_a_blocked_ticket_without_a_cause_has_no_motive() -> None:
    enveloppe = await _file([])
    await _enfant(enveloppe, "ticket-071", False, "blocked")

    assert _statut(enveloppe)["arretes"] == [{"ticket_id": "ticket-071", "motif": None}]


async def test_a_long_cause_is_cut_to_its_first_line() -> None:
    enveloppe = await _file([])
    await _enfant(enveloppe, "ticket-071", False, "blocked", "première ligne\n" + "x" * 500)

    assert _statut(enveloppe)["arretes"] == [
        {"ticket_id": "ticket-071", "motif": "première ligne"}
    ]


async def test_an_interrupted_ticket_is_stopped() -> None:
    enveloppe = await create_run(settings.ide_db_path, _PROJET, "queue", mode="queue")
    await create_run(settings.ide_db_path, _PROJET, "ticket-072", parent_run_id=enveloppe)
    await solder_les_runs_orphelins(settings.ide_db_path)

    corps = _statut(enveloppe)

    assert corps["approuves"] == []
    assert corps["arretes"] == [{"ticket_id": "ticket-072", "motif": CAUSE_RUN_ORPHELIN}]


async def test_a_ticket_cut_by_the_session_limit_is_left_to_do() -> None:
    enveloppe = await _file(["ticket-074"])
    await _enfant(enveloppe, "ticket-072", True, "done")
    await _enfant(enveloppe, "ticket-073", False, "todo", "session_limit (reprise : 18:00)")

    corps = _statut(enveloppe)

    assert corps["approuves"] == ["ticket-072"]
    assert corps["arretes"] == []
    assert corps["restants"] == ["ticket-073", "ticket-074"]
    assert corps["statut"] == "interrompu"


async def test_a_cut_ticket_already_announced_as_left_is_listed_once() -> None:
    enveloppe = await _file(["ticket-073"])
    await _enfant(enveloppe, "ticket-073", False, "todo", "run budget exhausted")

    assert _statut(enveloppe)["restants"] == ["ticket-073"]


async def test_faits_is_the_union_of_approved_and_stopped() -> None:
    enveloppe = await _file([])
    await _enfant(enveloppe, "ticket-070", True, "done")
    await _enfant(enveloppe, "ticket-071", False, "blocked", "refusé")
    await _enfant(enveloppe, "ticket-072", False, "todo", "session_limit")

    corps = _statut(enveloppe)

    assert corps["faits"] == ["ticket-070", "ticket-071"]
    assert corps["restants"] == ["ticket-072"]


async def test_a_child_without_an_end_under_a_finished_queue_is_never_approved() -> None:
    enveloppe = await _file([])
    await create_run(settings.ide_db_path, _PROJET, "ticket-075", parent_run_id=enveloppe)

    corps = _statut(enveloppe)

    assert corps["approuves"] == []
    assert corps["faits"] == ["ticket-075"]
