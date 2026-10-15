"""Un ticket dépendant ne part qu'une fois la PR de sa dépendance mergée — ticket-451.

La file attend `CIWatcher.attendre_merge`. Un ticket que le watcher n'a pas
inscrit — PR ouverte avec un `arret` (conflit résolu), donc jamais surveillée —
passait pour mergé. Ces tests câblent un vrai `CIWatcher`.
"""
import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services.ci_watcher import CIWatcher
from tessera.services.livraison import Livraison
from tessera.services.orchestrator import Orchestrator
from tessera.services.pipeline_events import PipelineResult


def _resultat(ticket_id: str) -> PipelineResult:
    return PipelineResult(
        ticket_id=ticket_id,
        final_status=TicketStatus.done,
        rounds=1,
        approved=True,
        branch=f"{ticket_id}-slug",
        commit_sha="abc",
    )


class _OrchestrateurDouble(Orchestrator):
    """Seul le pipeline interne est doublé : la file et l'attente sont réelles."""

    def __init__(self, resultats: list[PipelineResult], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._resultats = list(resultats)

    async def _run_pipeline(self, *args: Any, **kwargs: Any) -> PipelineResult:
        return self._resultats.pop(0)


def _tickets() -> AsyncMock:
    """Le ticket 002 dépend du 001."""

    def _ticket(tid: str, depends_on: list[str]) -> Ticket:
        return Ticket(
            id=tid, title="t", type=TicketType.feat, status=TicketStatus.todo,
            priority=TicketPriority.medium, agent="codeur", body="b",
            depends_on=depends_on,
        )

    par_id = {"ticket-001": _ticket("ticket-001", []),
              "ticket-002": _ticket("ticket-002", ["ticket-001"])}
    tickets = AsyncMock()
    tickets.get_ticket.side_effect = lambda tid: par_id.get(tid)
    return tickets


def _etat(valeur: str) -> Callable[[int], Awaitable[str]]:
    async def lire(pr_number: int) -> str:
        return valeur

    return lire


def _file(
    tmp_path: Path,
    livrer: Callable[[PipelineResult], Awaitable[Livraison]],
    watcher: CIWatcher,
    departs: list[str],
    etat_pr: Callable[[int], Awaitable[str]] | None,
    surveiller: Any = None,
) -> _OrchestrateurDouble:
    async def _livrer_et_noter(result: PipelineResult) -> Livraison:
        departs.append(result.ticket_id)
        return await livrer(result)

    return _OrchestrateurDouble(
        [_resultat("ticket-001"), _resultat("ticket-002")],
        runner=MagicMock(),
        ticket_service=_tickets(),
        project_context="ctx",
        agent_configs=[],
        pipeline_log_path=tmp_path / "memory" / "log.md",
        livrer=_livrer_et_noter,
        surveiller=surveiller,
        ci_watcher=watcher,
        etat_pr=etat_pr,
    )


async def _livraison_arretee(result: PipelineResult) -> Livraison:
    """PR ouverte mais livraison arrêtée : `surveiller` n'est jamais appelé."""
    return Livraison(pr_number=14, arret="conflit résolu, relecture requise")


async def test_dependant_ne_demarre_pas_quand_la_pr_n_est_pas_surveillee(
    tmp_path: Path,
) -> None:
    departs: list[str] = []
    orch = _file(tmp_path, _livraison_arretee, CIWatcher(), departs, _etat("open"))

    results = await orch.run_queue("proj", ["ticket-001", "ticket-002"])

    assert departs == ["ticket-001"]
    assert len(results) == 1


async def test_dependant_demarre_quand_la_pr_non_surveillee_est_mergee(
    tmp_path: Path,
) -> None:
    departs: list[str] = []
    orch = _file(tmp_path, _livraison_arretee, CIWatcher(), departs, _etat("merged"))

    results = await orch.run_queue("proj", ["ticket-001", "ticket-002"])

    assert departs == ["ticket-001", "ticket-002"]
    assert len(results) == 2


async def test_dependant_ne_demarre_pas_sans_lecteur_d_etat_de_pr(
    tmp_path: Path,
) -> None:
    departs: list[str] = []
    orch = _file(tmp_path, _livraison_arretee, CIWatcher(), departs, None)

    results = await orch.run_queue("proj", ["ticket-001", "ticket-002"])

    assert departs == ["ticket-001"]
    assert len(results) == 1


async def test_dependant_attend_le_merge_d_une_pr_surveillee(tmp_path: Path) -> None:
    gate = asyncio.Event()
    departs: list[str] = []
    watcher = CIWatcher()

    async def _phase2(pr_number: int) -> Livraison:
        await gate.wait()
        return Livraison(pr_number=pr_number, merged=True)

    async def _surveiller(
        project_id: str, ticket_id: str, pr_number: int, on_event: Any
    ) -> None:
        await watcher.surveiller(project_id, ticket_id, pr_number, _phase2, on_event)

    async def _livrer(result: PipelineResult) -> Livraison:
        return Livraison(pr_number=14, arret=None)

    # Un lecteur « open » prouve que la file suit le watcher, pas la relecture.
    orch = _file(tmp_path, _livrer, watcher, departs, _etat("open"), _surveiller)
    tache = asyncio.create_task(orch.run_queue("proj", ["ticket-001", "ticket-002"]))
    await asyncio.sleep(0.05)

    assert departs == ["ticket-001"]

    gate.set()
    results = await tache

    assert departs == ["ticket-001", "ticket-002"]
    assert len(results) == 2
    await watcher.arreter()
