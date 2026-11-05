"""A phase-one delivery stop without a PR blocks the ticket — ticket-741.

Couverture :
- un arrêt de phase 1 sans PR (tests rouges après rebase) bloque le ticket,
  émet `ticket_status_changed` et porte `final_status: blocked` ;
- l'arrêt voulu du niveau `commit` laisse le ticket `done` ;
- une livraison qui ouvre sa PR laisse le ticket `done` ;
- `Livraison.bloque_le_ticket` : branche modifiée, PR orpheline.
"""
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from tessera.models.ticket import TicketStatus
from tessera.services.livraison.livraison import Livraison, LivraisonService
from tessera.services.noyau.pipeline_events import EventType, OrchestratorEvent, PipelineResult
from tessera.services.pipeline.orchestrator import Orchestrator


def _resultat() -> PipelineResult:
    return PipelineResult(
        ticket_id="ticket-001",
        final_status=TicketStatus.done,
        rounds=1,
        approved=True,
        branch="ticket-001-slug",
        commit_sha="abc",
    )


class _OrchestrateurDouble(Orchestrator):
    """Only the inner pipeline is doubled; the delivery step is the real code."""

    async def _run_pipeline(self, *args: Any, **kwargs: Any) -> PipelineResult:
        return _resultat()


async def _executer(
    tmp_path: Path, livraison: Livraison
) -> tuple[PipelineResult, list[OrchestratorEvent]]:
    tickets = AsyncMock()
    tickets.get_ticket.return_value = None

    async def _livrer(resultat: PipelineResult) -> Livraison:
        return livraison

    orch = _OrchestrateurDouble(
        runner=MagicMock(),
        ticket_service=tickets,
        project_context="ctx",
        agent_configs=[],
        pipeline_log_path=tmp_path / "memory" / "log.md",
        livrer=_livrer,
    )
    recus: list[OrchestratorEvent] = []

    async def _capter(event: OrchestratorEvent) -> None:
        recus.append(event)

    resultat = await orch.run_pipeline("p", "ticket-001", _capter)
    return resultat, recus


def _statuts(evenements: list[OrchestratorEvent]) -> list[object]:
    return [
        e.data["status"]
        for e in evenements
        if e.type is EventType.TICKET_STATUS_CHANGED
    ]


async def test_phase_one_stop_without_pr_blocks_the_ticket(tmp_path: Path) -> None:
    livraison = Livraison(arret="Tests rouges après le rebase sur develop.")

    resultat, evenements = await _executer(tmp_path, livraison)

    assert _statuts(evenements) == [TicketStatus.blocked.value]
    assert resultat.final_status is TicketStatus.blocked
    assert resultat.arret == livraison.arret
    assert resultat.livraison == livraison


async def test_commit_level_stop_leaves_the_ticket_done(tmp_path: Path) -> None:
    livraison = Livraison(arret="commité sur ticket-001-slug", arret_voulu=True)

    resultat, evenements = await _executer(tmp_path, livraison)

    assert _statuts(evenements) == []
    assert resultat.final_status is TicketStatus.done


async def test_opened_pr_leaves_the_ticket_done(tmp_path: Path) -> None:
    resultat, evenements = await _executer(tmp_path, Livraison(pr_number=7))

    assert _statuts(evenements) == []
    assert resultat.final_status is TicketStatus.done


async def test_commit_level_service_marks_its_stop_as_wanted(tmp_path: Path) -> None:
    (tmp_path / "agents.json").write_text('{"autonomy": "commit"}', encoding="utf-8")
    service = LivraisonService(
        git_workspace=AsyncMock(),
        workflow=AsyncMock(),
        project_path=tmp_path,
        base_branch="develop",
    )

    livraison = await service.livrer_phase_1(
        ticket_id="ticket-001",
        ticket_title="T",
        ticket_body="",
        branch="ticket-001-slug",
        approuve=True,
    )

    assert livraison.arret_voulu
    assert not livraison.bloque_le_ticket


def test_blocking_rule_covers_each_kind_of_stop() -> None:
    assert Livraison(branche_modifiee=True, arret="x").bloque_le_ticket
    assert Livraison(arret="rebase refusé").bloque_le_ticket
    assert not Livraison().bloque_le_ticket
    orpheline = Livraison(arret="levée après la PR", pr_number=7, pr_orpheline=True)
    assert not orpheline.bloque_le_ticket
