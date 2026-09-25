"""L'avancement d'une file voyage dans l'instantane — ticket-172.

Une file est *un* run (ADR-041), donc une carte. Sans ces champs, la
Supervision ne pouvait pas dire s'il en restait deux derriere.
"""

from tessera.models.agent import AgentRole
from tessera.services.pipeline_events import EventType, OrchestratorEvent
from tessera.services.run_executor import _suivre
from tessera.services.run_registry import RunActif


def _run(mode: str = "queue") -> RunActif:
    return RunActif(run_id="r1", project_id="demineur", mode=mode)


def _progres(index: int, total: int, restants: list[str]) -> OrchestratorEvent:
    return OrchestratorEvent(
        type=EventType.QUEUE_PROGRESS,
        ticket_id="ticket-004",
        agent=AgentRole.codeur,
        data={"index": index, "total": total, "restants": restants},
    )


def test_l_avancement_est_retenu() -> None:
    run = _run()

    _suivre(run, _progres(2, 3, ["ticket-005"]))

    assert (run.file_index, run.file_total) == (2, 3)


def test_les_tickets_restants_sont_retenus() -> None:
    run = _run()

    _suivre(run, _progres(1, 3, ["ticket-005", "ticket-006"]))

    assert run.file_restants == ("ticket-005", "ticket-006")


def test_l_avancement_part_dans_l_instantane() -> None:
    """Sinon un observateur arrive en cours de file ne le verra jamais."""
    run = _run()
    _suivre(run, _progres(2, 3, ["ticket-005"]))

    corps = run.en_dict()

    assert corps["file_index"] == 2
    assert corps["file_total"] == 3
    assert corps["file_restants"] == ["ticket-005"]


def test_un_run_unique_n_a_pas_d_avancement() -> None:
    run = _run(mode="single")

    corps = run.en_dict()

    assert corps["file_total"] == 0
    assert corps["file_restants"] == []


def test_un_progres_plus_recent_remplace_le_precedent() -> None:
    run = _run()
    _suivre(run, _progres(1, 3, ["ticket-005", "ticket-006"]))

    _suivre(run, _progres(2, 3, ["ticket-006"]))

    assert run.file_index == 2
    assert run.file_restants == ("ticket-006",)
