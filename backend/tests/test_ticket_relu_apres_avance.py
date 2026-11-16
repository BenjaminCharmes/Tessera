"""The ticket is read again once the base is advanced — ticket-977."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services.noyau.pipeline_events import EventType, OrchestratorEvent
from tessera.services.pipeline.orchestrator import Orchestrator
from tessera.services.pipeline.pipeline_run import PipelineRun
from tessera.services.pipeline.ticket_apres_avance import relire_apres_branche


def _fiche(body: str, preuve: bool = False) -> Ticket:
    return Ticket(
        id="ticket-100", title="t", type=TicketType.feat, status=TicketStatus.todo,
        priority=TicketPriority.medium, agent="codeur", body=body, preuve_reelle=preuve,
    )


def _orch(fiches: list[Ticket | None]) -> tuple[Orchestrator, MagicMock]:
    svc = MagicMock()
    svc.get_ticket = AsyncMock(side_effect=fiches)
    git = MagicMock()
    git.head_sha = AsyncMock(return_value="b" * 40)
    orch = object.__new__(Orchestrator)
    orch._ticket_svc = svc
    orch._git_workspace = git
    orch._worktree = None
    orch._preuves_reelles = {}
    orch._log = MagicMock()  # type: ignore[method-assign]
    return orch, svc


def _run(ticket: Ticket, evenements: list[OrchestratorEvent]) -> PipelineRun:
    async def on_event(e: OrchestratorEvent) -> None:
        evenements.append(e)

    return PipelineRun(project_id="p", ticket=ticket, on_event=on_event)


async def test_changed_text_replaces_ticket_and_announces_it() -> None:
    orch, _ = _orch([_fiche("B", preuve=True)])
    evenements: list[OrchestratorEvent] = []
    run = _run(_fiche("A"), evenements)
    orch._preuves_reelles["ticket-100"] = False

    assert await relire_apres_branche(orch, run, "a" * 40) is None

    assert run.ticket.body == "B"
    assert orch._preuves_reelles["ticket-100"] is True
    assert [e.type for e in evenements] == [EventType.TICKET_RELU_APRES_AVANCE]
    assert evenements[0].data == {"ancien_sha": "a" * 40, "nouveau_sha": "b" * 40}
    orch._log.assert_called_once()


async def test_unchanged_text_emits_nothing() -> None:
    orch, _ = _orch([_fiche("A")])
    evenements: list[OrchestratorEvent] = []
    run = _run(_fiche("A"), evenements)

    assert await relire_apres_branche(orch, run, "a" * 40) is None

    assert evenements == []
    orch._log.assert_not_called()


async def test_missing_ticket_after_advance_blocks() -> None:
    orch, _ = _orch([None])
    run = _run(_fiche("A"), [])

    resultat = await relire_apres_branche(orch, run, None)

    assert resultat is not None
    assert resultat.final_status == TicketStatus.blocked
    assert resultat.arret is not None and "ticket-100" in resultat.arret


async def test_run_worktree_keeps_its_ticket() -> None:
    orch, svc = _orch([_fiche("B")])
    orch._worktree = object()
    run = _run(_fiche("A"), [])

    assert await relire_apres_branche(orch, run, None) is None
    assert run.ticket.body == "A"
    svc.get_ticket.assert_not_called()


@pytest.fixture
def _stages(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "tessera.services.pipeline.orchestrator.activer_enregistrement", MagicMock()
    )
    for nom in ("ensure_clean_tree", "create_branch"):
        monkeypatch.setattr(
            f"tessera.services.pipeline.pipeline_branche.{nom}", AsyncMock(return_value=None)
        )


async def test_pipeline_blocks_without_agent_when_ticket_vanishes(_stages: None) -> None:
    orch, _ = _orch([_fiche("A"), None])
    orch._run_rounds = AsyncMock()  # type: ignore[method-assign]

    resultat = await orch._run_pipeline("p", "ticket-100", AsyncMock())

    assert resultat.final_status == TicketStatus.blocked
    assert not resultat.approved
    orch._run_rounds.assert_not_called()
    assert orch._preuves_reelles["ticket-100"] is False
