"""The coder reads the reviewer's whole objection, and the log shows its first reason — ticket-474."""
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

from tessera.models.agent import AgentResult, AgentRole
from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services.orchestrator import Orchestrator, OrchestratorEvent
from tessera.services.pipeline_text import OBJECTION_MAX_CHARS, _first_line
from tessera.services.verdict_reviewer import lire_verdict
from tests.revue_structuree import revue

THREE_REMARKS = revue(
    "CHANGES_REQUESTED",
    ("Le endpoint renvoie 200 au lieu de 404 quand la liste est absente.", 95),
    ("Le test de pagination ne couvre pas la dernière page.", 90),
    ("Le message d'erreur n'est pas traduit.", 85),
)


async def _noop(event: OrchestratorEvent) -> None:
    pass


class _ScriptedRunner:
    """Reviewer answers with a fixed refusal; records what the coder is given."""

    def __init__(self, review: dict[str, Any]) -> None:
        self._review = review
        self.coder_contexts: list[str] = []

    async def run(self, **kwargs: object) -> AgentResult:
        role = kwargs["role"]
        if role == AgentRole.codeur:
            self.coder_contexts.append(str(kwargs["project_context"]))
        structured = self._review if role == AgentRole.reviewer else None
        return AgentResult(
            role=role,  # type: ignore[arg-type]
            ticket_id="ticket-001",
            content="prose du codeur",
            structured=structured,
            suggested_status=TicketStatus.in_review,
            duration_ms=1,
        )


async def _run_two_rounds(tmp_path: Path, review: dict[str, Any]) -> tuple[_ScriptedRunner, str]:
    ticket = Ticket(
        id="ticket-001",
        title="Test feature",
        type=TicketType.feat,
        status=TicketStatus.todo,
        priority=TicketPriority.medium,
        agent="codeur",
        body="Implement the feature.",
    )
    svc = AsyncMock()
    svc.get_ticket.return_value = ticket
    svc.update_status.return_value = ticket
    runner = _ScriptedRunner(review)
    log_path = tmp_path / "memory" / "pipeline-log.md"
    orc = Orchestrator(
        runner=runner,  # type: ignore[arg-type]
        ticket_service=svc,
        project_context="ctx",
        agent_configs=[],
        pipeline_log_path=log_path,
        max_review_rounds=2,
    )
    await orc.run_pipeline("proj", "ticket-001", _noop)
    return runner, log_path.read_text(encoding="utf-8")


def test_a_refusal_reads_every_blocking_remark_as_its_reason() -> None:
    approved, reason = lire_verdict(THREE_REMARKS, 80)

    assert approved is False
    assert "Le endpoint renvoie 200 au lieu de 404" in reason
    assert "dernière page" in reason
    assert "CHANGES_REQUESTED" not in reason


def test_a_refusal_without_remark_keeps_the_summary_as_reason() -> None:
    _, reason = lire_verdict(revue("CHANGES_REQUESTED", summary="tests manquants"), 80)

    assert reason == "tests manquants"


def test_the_summary_follows_the_remarks_in_the_reason() -> None:
    answer = revue("CHANGES_REQUESTED", ("le point bloquant", 90), summary="Détail.")

    _, reason = lire_verdict(answer, 80)

    assert reason.startswith("1. le point bloquant")
    assert reason.endswith("Détail.")


def test_first_line_skips_blank_lines() -> None:
    assert _first_line("\n\n  premiere  \nseconde") == "premiere"
    assert _first_line("  \n") == ""


async def test_an_objection_of_3000_chars_reaches_the_coder_whole(tmp_path: Path) -> None:
    objection = "a" * 3000

    runner, _ = await _run_two_rounds(
        tmp_path, revue("CHANGES_REQUESTED", (objection, 100))
    )

    second_round = runner.coder_contexts[1]
    assert objection in second_round
    assert "tronqué" not in second_round


async def test_an_objection_of_6000_chars_is_cut_at_4000(tmp_path: Path) -> None:
    objection = "b" * 6000

    runner, _ = await _run_two_rounds(
        tmp_path, revue("CHANGES_REQUESTED", (objection, 100))
    )

    second_round = runner.coder_contexts[1]
    # La raison commence par « 1. » : la coupe tombe donc à 4000 caractères
    # de raison, quelques `b` avant 4000.
    assert "b" * (OBJECTION_MAX_CHARS - 10) in second_round
    assert "b" * OBJECTION_MAX_CHARS not in second_round
    assert "tronqué" in second_round


async def test_the_log_line_shows_the_first_line_of_the_reason(tmp_path: Path) -> None:
    _, log = await _run_two_rounds(tmp_path, THREE_REMARKS)

    refusal_lines = [ln for ln in log.splitlines() if "CHANGES_REQUESTED tour 1" in ln]
    assert len(refusal_lines) == 1
    assert "Le endpoint renvoie 200 au lieu de 404" in refusal_lines[0]
    assert "dernière page" not in refusal_lines[0]
