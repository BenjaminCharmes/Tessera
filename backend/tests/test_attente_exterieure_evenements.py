"""The queue announces its waits on an outside event — ticket-559.

`external_wait` goes `waiting: true` before the queue suspends on a PR another
ticket depends on, and `waiting: false` after, however the wait ends. A queue
that does not suspend says nothing.
"""
import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from tessera.config import settings
from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services.attente_dependance import attendre_si_dependant as _attendre_si_dependant
from tessera.services.ci_watcher import CIWatcher
from tessera.services.database import create_run, get_run_events, init_db
from tessera.services.event_hub import EventHub
from tessera.services.livraison import Livraison
from tessera.services.orchestrator import Orchestrator
from tessera.services.pipeline_events import EventType, OrchestratorEvent, PipelineResult
from tessera.services.run_executor import emetteur
from tessera.services.run_registry import RunActif


def _resultat(ticket_id: str) -> PipelineResult:
    return PipelineResult(
        ticket_id=ticket_id, final_status=TicketStatus.done, rounds=1,
        approved=True, branch=f"{ticket_id}-slug", commit_sha="abc",
    )


def _ticket(tid: str, depends_on: list[str]) -> Ticket:
    return Ticket(
        id=tid, title="t", type=TicketType.feat, status=TicketStatus.todo,
        priority=TicketPriority.medium, agent="codeur", body="b", depends_on=depends_on,
    )


def _tickets(deps_du_002: list[str]) -> AsyncMock:
    par_id = {
        "ticket-001": _ticket("ticket-001", []),
        "ticket-002": _ticket("ticket-002", deps_du_002),
    }
    tickets = AsyncMock()
    tickets.get_ticket.side_effect = lambda tid: par_id.get(tid)
    return tickets


class _Orchestrateur(Orchestrator):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._resultats = [_resultat("ticket-001"), _resultat("ticket-002")]

    async def _run_pipeline(self, *args: Any, **kwargs: Any) -> PipelineResult:
        return self._resultats.pop(0)


def _file(
    tmp_path: Path,
    watcher: CIWatcher,
    livraison: Livraison,
    etat_pr: str,
    surveiller: Any = None,
    deps_du_002: list[str] | None = None,
) -> _Orchestrateur:
    async def _livrer(result: PipelineResult) -> Livraison:
        return livraison

    async def _etat(pr_number: int) -> str:
        return etat_pr

    return _Orchestrateur(
        runner=MagicMock(),
        ticket_service=_tickets(["ticket-001"] if deps_du_002 is None else deps_du_002),
        project_context="ctx",
        agent_configs=[],
        pipeline_log_path=tmp_path / "memory" / "log.md",
        livrer=_livrer,
        surveiller=surveiller,
        ci_watcher=watcher,
        etat_pr=_etat,
    )


def _recueil() -> tuple[list[OrchestratorEvent], Callable[[OrchestratorEvent], Awaitable[None]]]:
    recus: list[OrchestratorEvent] = []

    async def on_event(event: OrchestratorEvent) -> None:
        recus.append(event)

    return recus, on_event


def _attentes(recus: list[OrchestratorEvent]) -> list[dict[str, Any]]:
    return [e.data for e in recus if e.type is EventType.EXTERNAL_WAIT]


async def test_a_queue_waiting_for_a_merge_announces_the_wait_then_its_end(
    tmp_path: Path,
) -> None:
    gate = asyncio.Event()
    watcher = CIWatcher()

    async def _phase2(pr_number: int) -> Livraison:
        await gate.wait()
        return Livraison(pr_number=pr_number, merged=True)

    async def _surveiller(p: str, t: str, pr: int, on_event: Any) -> None:
        await watcher.surveiller(p, t, pr, _phase2, on_event)

    recus, on_event = _recueil()
    orch = _file(tmp_path, watcher, Livraison(pr_number=14), "open", _surveiller)
    tache = asyncio.create_task(
        orch.run_queue("proj", ["ticket-001", "ticket-002"], on_event=on_event)
    )
    await asyncio.sleep(0.05)

    assert _attentes(recus) == [
        {"reason": "dependency", "waiting": True, "ticket": "ticket-001", "pr_number": 14}
    ]

    gate.set()
    await tache

    assert [a["waiting"] for a in _attentes(recus)] == [True, False]
    await watcher.arreter()


async def test_a_refused_merge_still_announces_the_end_of_the_wait(tmp_path: Path) -> None:
    recus, on_event = _recueil()
    # PR ouverte avec un arrêt, jamais surveillée, et toujours « open » : refus.
    orch = _file(
        tmp_path, CIWatcher(), Livraison(pr_number=14, arret="conflit"), "open"
    )

    results = await orch.run_queue("proj", ["ticket-001", "ticket-002"], on_event=on_event)

    assert len(results) == 1
    assert [a["waiting"] for a in _attentes(recus)] == [True, False]


async def test_a_cancelled_wait_still_announces_its_end() -> None:
    recus, on_event = _recueil()
    watcher = MagicMock()
    entree = asyncio.Event()

    async def _attendre(*args: Any, **kwargs: Any) -> bool:
        entree.set()
        await asyncio.Event().wait()
        return True

    watcher.attendre_merge = _attendre
    tickets = _tickets(["ticket-001"])
    tache = asyncio.create_task(
        _attendre_si_dependant(
            tickets, watcher, "proj", "ticket-001", ["ticket-002"], pr_number=14,
            on_event=on_event,
        )
    )
    await entree.wait()
    tache.cancel()
    with pytest.raises(asyncio.CancelledError):
        await tache

    assert [a["waiting"] for a in _attentes(recus)] == [True, False]


async def test_a_queue_with_no_dependent_ticket_announces_no_wait(tmp_path: Path) -> None:
    recus, on_event = _recueil()
    orch = _file(
        tmp_path, CIWatcher(), Livraison(pr_number=14), "open", deps_du_002=[]
    )

    results = await orch.run_queue("proj", ["ticket-001", "ticket-002"], on_event=on_event)

    assert len(results) == 2
    assert _attentes(recus) == []


async def test_the_new_events_are_persisted_and_replayed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "t.db"
    await init_db(db)
    monkeypatch.setattr(settings, "ide_db_path", db)
    run_id = await create_run(db, "p", "ticket-001")
    envoyer = emetteur(EventHub(), RunActif(run_id="r", project_id="p", ticket_id="ticket-001"), run_id)

    await envoyer(OrchestratorEvent(
        type=EventType.EXTERNAL_WAIT, ticket_id="ticket-001",
        data={"reason": "dependency", "waiting": True, "ticket": "ticket-001", "pr_number": 14},
    ))
    await envoyer(OrchestratorEvent(
        type=EventType.CONFLICT_RESOLUTION, ticket_id="ticket-001",
        data={"phase": "started", "files": ["a.py"], "outcome": None},
    ))

    events = await get_run_events(db, run_id)

    assert events is not None
    assert [e["type"] for e in events] == ["external_wait", "conflict_resolution"]
