"""The codeur's exhausted turns are journaled — ticket-702.

Covers:
- ``AgentRunner`` carries ``num_turns`` / ``max_turns_reached`` from the provider
  result to the ``AgentResult``;
- ``run_coder`` writes ``codeur : actions épuisées (<n>/<limite>)`` only when the
  limit was reached, and the run goes on to the diff capture as before;
- the ``AGENT_DONE`` event carries ``turns`` and ``turns_exhausted``.
"""
from pathlib import Path
from unittest.mock import AsyncMock

from tessera.config import settings
from tessera.models.agent import AgentResult
from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services.pipeline import pipeline_production
from tessera.services.pipeline.orchestrator import Orchestrator
from tessera.services.pipeline_events import EventType, OrchestratorEvent
from tessera.services.pipeline.pipeline_run import PipelineRun


def _ticket() -> Ticket:
    return Ticket(
        id="ticket-702", title="t", type=TicketType.feat, status=TicketStatus.todo,
        priority=TicketPriority.medium, agent="codeur", body="## Critères\n- [ ] ok\n",
    )


async def _tour_de_codeur(
    tmp_path: Path, *, num_turns: int | None, epuise: bool
) -> tuple[list[str], list[OrchestratorEvent]]:
    journal = tmp_path / "memory" / "pipeline-log.md"
    journal.parent.mkdir(parents=True)
    ticket = _ticket()
    runner = AsyncMock()
    runner.run.return_value = AgentResult(
        role="codeur", ticket_id=ticket.id, content="travail partiel",
        suggested_status=TicketStatus.in_review, duration_ms=5,
        num_turns=num_turns, max_turns_reached=epuise,
    )
    orch = Orchestrator(
        runner=runner, ticket_service=AsyncMock(), project_context="ctx",
        agent_configs=[], pipeline_log_path=journal,
    )
    evenements: list[OrchestratorEvent] = []

    async def _on_event(event: OrchestratorEvent) -> None:
        evenements.append(event)

    run = PipelineRun(project_id="proj", ticket=ticket, on_event=_on_event)
    run.start_round(1)
    await pipeline_production.run_coder(orch, run, "contexte")
    return journal.read_text(encoding="utf-8").splitlines(), evenements


async def test_run_coder_journals_exhausted_turns(tmp_path: Path) -> None:
    lignes, evenements = await _tour_de_codeur(tmp_path, num_turns=30, epuise=True)

    attendu = (
        f"[ticket-702] tour 1 — codeur : actions épuisées (30/{settings.llm_max_turns})"
    )
    assert any(ligne.endswith(attendu) for ligne in lignes)
    termine = [e for e in evenements if e.type == EventType.AGENT_DONE][0]
    assert termine.data["turns"] == 30
    assert termine.data["turns_exhausted"] is True


async def test_run_coder_journals_nothing_when_turns_remain(tmp_path: Path) -> None:
    lignes, evenements = await _tour_de_codeur(tmp_path, num_turns=7, epuise=False)

    assert not any("actions épuisées" in ligne for ligne in lignes)
    termine = [e for e in evenements if e.type == EventType.AGENT_DONE][0]
    assert termine.data["turns"] == 7
    assert termine.data["turns_exhausted"] is False


async def test_exhausted_turns_do_not_change_the_run_course(tmp_path: Path) -> None:
    _, evenements = await _tour_de_codeur(tmp_path, num_turns=30, epuise=True)

    # Le tour finit comme un tour ordinaire : même suite d'événements que sans
    # épuisement, aucun refus ni repli ajouté.
    _, ordinaires = await _tour_de_codeur(
        tmp_path / "ordinaire", num_turns=7, epuise=False
    )
    assert [e.type for e in evenements] == [e.type for e in ordinaires]
    assert evenements[0].type == EventType.AGENT_STARTED
