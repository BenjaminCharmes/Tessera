"""The helpers the review stage calls — ticket-614 (ADR-061)."""
from tessera.config import settings
from tessera.models.agent import AgentResult, AgentRole
from tessera.models.ticket import TicketStatus
from tessera.services.verdict_reviewer import donnees_fin_de_revue, juger_revue
from tests.revue_structuree import revue


def _result() -> AgentResult:
    return AgentResult(
        role=AgentRole.reviewer,
        ticket_id="ticket-001",
        content="",
        suggested_status=TicketStatus.in_review,
        cost_usd=0.5,
        duration_ms=42,
    )


def test_juger_revue_reads_the_answer_at_the_configured_threshold() -> None:
    score = settings.reviewer_confidence_threshold - 1
    answer = revue("CHANGES_REQUESTED", ("détail mineur", score))

    approved, reason, text = juger_revue(answer)

    assert approved is True
    assert reason == ""
    assert text.splitlines()[0] == "APPROVED"


def test_juger_revue_refuses_an_absent_answer() -> None:
    approved, reason, text = juger_revue(None)

    assert approved is False
    assert "absente" in reason
    assert text.splitlines()[0] == "CHANGES_REQUESTED"


def test_juger_revue_keeps_a_blocking_remark_in_the_rendered_review() -> None:
    answer = revue("CHANGES_REQUESTED", ("faille ouverte", 100))

    approved, reason, text = juger_revue(answer)

    assert approved is False
    assert "faille ouverte" in reason
    assert "faille ouverte" in text


def test_donnees_fin_de_revue_carries_the_kept_verdict_and_the_figures() -> None:
    data = donnees_fin_de_revue(True, "APPROVED", _result())

    assert data == {
        "content": "APPROVED",
        "verdict": "APPROVED",
        "cost_usd": 0.5,
        "duration_ms": 42,
    }
    assert donnees_fin_de_revue(False, "x", _result())["verdict"] == "CHANGES_REQUESTED"
