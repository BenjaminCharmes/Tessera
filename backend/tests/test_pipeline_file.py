"""Queue helpers split out of the orchestrator — ticket-685."""
from types import SimpleNamespace
from typing import cast

from tessera.services.orchestrator import Orchestrator
from tessera.services.pipeline_events import EventType, OrchestratorEvent
from tessera.services.pipeline_file import plafond_effectif
from tessera.services.pipeline_file_tour import Tour, progres


def _orch(plafond_par_ticket: float) -> Orchestrator:
    return cast(Orchestrator, SimpleNamespace(_run_max_budget_usd=plafond_par_ticket))


def test_ceiling_is_the_per_ticket_ceiling_times_the_ticket_count() -> None:
    assert plafond_effectif(_orch(2.0), 3, None) == 6.0


def test_ceiling_override_replaces_the_computed_one() -> None:
    assert plafond_effectif(_orch(2.0), 3, 1.5) == 1.5


def test_no_per_ticket_ceiling_means_no_queue_ceiling() -> None:
    assert plafond_effectif(_orch(0.0), 3, None) == 0.0


def test_tour_payload_names_the_done_and_remaining_tickets() -> None:
    tour = Tour("p", ["a", "b", "c"], 2, "b")

    assert tour.restants == ["c"]
    assert tour.donnees() == {
        "index": 2, "total": 3, "restants": ["c"], "faits": ["a"],
    }


def test_tour_payload_can_start_remaining_at_the_current_ticket() -> None:
    tour = Tour("p", ["a", "b", "c"], 2, "b")

    assert tour.donnees(depuis=1)["restants"] == ["b", "c"]


async def test_progress_emits_a_queue_progress_event() -> None:
    recus: list[OrchestratorEvent] = []

    async def collecter(event: OrchestratorEvent) -> None:
        recus.append(event)

    await progres(collecter, "t-1", {"index": 1})

    assert [(e.type, e.ticket_id, e.data) for e in recus] == [
        (EventType.QUEUE_PROGRESS, "t-1", {"index": 1})
    ]
