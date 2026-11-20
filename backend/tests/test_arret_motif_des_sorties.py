"""Every unapproved end of a run states why it stopped — ticket-985."""
import inspect
import sqlite3
from collections.abc import Awaitable, Callable

import pytest

from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services.noyau.pipeline_events import OrchestratorEvent, PipelineResult
from tessera.services.pipeline import pipeline_outcomes as outcomes
from tessera.services.pipeline.pipeline_run import PipelineRun
from tessera.services.pipeline.run_status import classer_les_tickets
from tests.doubles_git import GitWorkspaceDouble
from tests.test_commit_sur_toutes_les_sorties import _GitQuiEchoue


class _Tickets:
    async def update_status(self, ticket_id: str, status: TicketStatus) -> None:
        return None


class _Orch:
    def __init__(self, git: GitWorkspaceDouble) -> None:
        self._git_workspace = git
        self._ticket_svc = _Tickets()
        self._max_review_rounds = 3
        self._run_max_budget_usd = 1.0
        self.spent_ticket_usd = 2.0

    def _log(self, message: str) -> None:
        return None


def _run() -> PipelineRun:
    async def _on_event(event: OrchestratorEvent) -> None:
        return None

    ticket = Ticket(
        id="ticket-001", title="T", type=TicketType.feat, status=TicketStatus.in_progress,
        priority=TicketPriority.medium, agent="codeur", body="",
    )
    run = PipelineRun(project_id="p", ticket=ticket, on_event=_on_event)
    run.branch = "ticket-001-x"
    run.round_num = 1
    return run


_Fin = Callable[[_Orch, PipelineRun], Awaitable[PipelineResult]]
_FINS: dict[str, _Fin] = {
    "finish_timeout_expired": lambda o, r: outcomes.finish_timeout_expired(o, r),  # type: ignore[arg-type]
    "finish_security_block": lambda o, r: outcomes.finish_security_block(o, r, "faille\nsuite"),  # type: ignore[arg-type]
    "finish_stopped": lambda o, r: outcomes.finish_stopped(o, r),  # type: ignore[arg-type]
    "finish_rounds_exhausted": lambda o, r: outcomes.finish_rounds_exhausted(o, r),  # type: ignore[arg-type]
    "finish_budget_exhausted": lambda o, r: outcomes.finish_budget_exhausted(o, r),  # type: ignore[arg-type]
    "finish_budget_exhausted_in_queue": lambda o, r: outcomes.finish_budget_exhausted_in_queue(o, r),  # type: ignore[arg-type]
    "finish_session_limit": lambda o, r: outcomes.finish_session_limit(o, r, RuntimeError(), None),  # type: ignore[arg-type]
    "finish_quota_exhausted": lambda o, r: outcomes.finish_quota_exhausted(o, r, RuntimeError(), "demain"),  # type: ignore[arg-type]
    "finish_interrupted": lambda o, r: outcomes.finish_interrupted(o, r, RuntimeError("boom")),  # type: ignore[arg-type]
}


def test_the_table_covers_every_unapproved_finish() -> None:
    publics = {
        n for n, f in inspect.getmembers(outcomes, inspect.iscoroutinefunction)
        if n.startswith("finish_") and n != "finish_approved" and f.__module__ == outcomes.__name__
    }
    assert publics == set(_FINS)


@pytest.mark.parametrize("nom", sorted(_FINS))
async def test_an_unapproved_finish_never_leaves_arret_empty(nom: str) -> None:
    resultat = await _FINS[nom](_Orch(GitWorkspaceDouble()), _run())
    assert resultat.approved is False
    assert (resultat.arret or "").strip()


async def test_security_block_arret_carries_the_first_summary_line() -> None:
    resultat = await _FINS["finish_security_block"](_Orch(GitWorkspaceDouble()), _run())
    assert resultat.arret is not None
    assert resultat.arret.startswith("audit sécurité : ")
    assert "faille" in resultat.arret
    assert "suite" not in resultat.arret


async def test_stopped_and_rounds_exhausted_have_their_own_reason() -> None:
    arret = await _FINS["finish_stopped"](_Orch(GitWorkspaceDouble()), _run())
    tours = await _FINS["finish_rounds_exhausted"](_Orch(GitWorkspaceDouble()), _run())
    assert arret.arret == "arrêté à la demande"
    assert tours.arret == "non approuvé après 3 tours"


@pytest.mark.parametrize("nom", ["finish_security_block", "finish_stopped", "finish_rounds_exhausted"])
async def test_a_failed_commit_keeps_priority_over_the_reason(nom: str) -> None:
    resultat = await _FINS[nom](_Orch(_GitQuiEchoue()), _run())
    assert (resultat.arret or "").startswith("commit_failed")


async def test_classer_les_tickets_gives_a_motif_for_a_security_block() -> None:
    resultat = await _FINS["finish_security_block"](_Orch(GitWorkspaceDouble()), _run())
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("CREATE TABLE r (ticket_id, approved, final_status, arret, finished_at)")
    db.execute(
        "INSERT INTO r VALUES (?,?,?,?,?)",
        ("ticket-001", 0, "blocked", resultat.arret, "2026-11-17T10:00:00"),
    )
    classement = classer_les_tickets(list(db.execute("SELECT * FROM r")), True)
    assert classement.arretes[0].motif is not None
    assert classement.arretes[0].motif.startswith("audit sécurité")
