"""The reviewer verdict is read from a structured output — ticket-614 (ADR-061).

Covers `lire_verdict` and `rendre_revue` as pure functions, then the pipeline
stage that feeds them. The scenarios of tickets 122, 298, 474 and 574 keep
their meaning here, in structured form.
"""
import re
from pathlib import Path
from typing import Any

import pytest

from tessera.config import Settings, settings
from tessera.models.agent import AgentResult, AgentRole
from tessera.models.ticket import TicketStatus
from tessera.services.orchestrator import EventType, OrchestratorEvent
from tessera.services.reviewer_schema import REVIEWER_SCHEMA
from tessera.services.verdict_reviewer import lire_verdict, rendre_revue
from tests.revue_structuree import revue
from tests.test_orchestrator import _make_orchestrator, _noop

ROOT = Path(__file__).resolve().parents[2]
PROMPT = ROOT / "agents" / "prompts" / "reviewer.md"
SRC = ROOT / "backend" / "src"


# ------------------------------------------------------------------
# lire_verdict — les sept cas du ticket
# ------------------------------------------------------------------


def test_absent_structured_output_refuses() -> None:
    approved, reason = lire_verdict(None, 80)

    assert approved is False
    assert "absente" in reason


@pytest.mark.parametrize("missing", ["verdict", "summary", "blocking"])
def test_a_missing_required_field_refuses_and_names_it(missing: str) -> None:
    answer = revue("APPROVED")
    del answer[missing]

    approved, reason = lire_verdict(answer, 80)

    assert approved is False
    assert missing in reason


def test_a_verdict_outside_the_enum_refuses() -> None:
    approved, reason = lire_verdict(revue("LGTM"), 80)

    assert approved is False
    assert "LGTM" in reason


@pytest.mark.parametrize("confidence", [-1, 101, 1000])
def test_a_confidence_outside_0_100_refuses(confidence: int) -> None:
    approved, reason = lire_verdict(
        revue("CHANGES_REQUESTED", ("bug", confidence)), 80
    )

    assert approved is False
    assert "confidence" in reason


@pytest.mark.parametrize("confidence", ["90", 90.5, True, None])
def test_a_confidence_that_is_not_an_integer_refuses(confidence: Any) -> None:
    answer = revue("CHANGES_REQUESTED", ("bug", 0))
    answer["blocking"][0]["confidence"] = confidence

    assert lire_verdict(answer, 80)[0] is False


def test_a_remark_without_confidence_refuses() -> None:
    answer = revue("CHANGES_REQUESTED", ("bug", 10))
    del answer["blocking"][0]["confidence"]

    approved, reason = lire_verdict(answer, 80)

    assert approved is False
    assert "confidence" in reason


def test_changes_requested_with_a_remark_over_the_threshold_refuses() -> None:
    answer = revue("CHANGES_REQUESTED", ("léger", 30), ("grave", 90), ("doute", 50))

    approved, reason = lire_verdict(answer, 80)

    assert approved is False
    assert "grave" in reason


def test_a_remark_equal_to_the_threshold_blocks() -> None:
    assert lire_verdict(revue("CHANGES_REQUESTED", ("bug", 80)), 80)[0] is False


def test_changes_requested_with_every_remark_under_the_threshold_approves() -> None:
    answer = revue("CHANGES_REQUESTED", ("doute", 40), ("autre doute", 79))

    assert lire_verdict(answer, 80) == (True, "")


def test_a_zero_threshold_turns_the_filter_off() -> None:
    assert lire_verdict(revue("CHANGES_REQUESTED", ("doute", 10)), 0)[0] is False


def test_changes_requested_without_remark_refuses_with_the_summary() -> None:
    answer = revue("CHANGES_REQUESTED", summary="Le périmètre n'est pas couvert.")

    assert lire_verdict(answer, 80) == (False, "Le périmètre n'est pas couvert.")


def test_approved_with_a_remark_over_the_threshold_contradicts_itself() -> None:
    approved, reason = lire_verdict(revue("APPROVED", ("bug réel", 95)), 80)

    assert approved is False
    assert "Contradiction" in reason
    assert "bug réel" in reason


def test_approved_with_a_remark_under_the_threshold_approves() -> None:
    assert lire_verdict(revue("APPROVED", ("détail", 20)), 80) == (True, "")


def test_a_clean_approval_approves() -> None:
    assert lire_verdict(revue("APPROVED", summary="Tout est bon."), 80) == (True, "")


# ------------------------------------------------------------------
# Les scénarios des tickets 122 et 298, sous leur forme structurée
# ------------------------------------------------------------------


def test_a_summary_that_denies_approval_approves_nothing() -> None:
    # Ticket-122 : « this should not be approved » était lu comme un verdict.
    answer = revue("CHANGES_REQUESTED", summary="This should not be approved.")

    assert lire_verdict(answer, 80)[0] is False


def test_an_approval_that_quotes_changes_requested_still_approves() -> None:
    # Ticket-298 : le corps citait `CHANGES_REQUESTED`, trois APPROVED refusés.
    summary = "- **Bug `CHANGES_REQUESTED` réellement corrigé** — le motif est journalisé."

    assert lire_verdict(revue("APPROVED", summary=summary), 80) == (True, "")


def test_prose_in_the_summary_never_overrides_the_verdict_field() -> None:
    answer = revue("CHANGES_REQUESTED", ("manque un test", 90), summary="APPROVED")

    assert lire_verdict(answer, 80)[0] is False


# ------------------------------------------------------------------
# rendre_revue
# ------------------------------------------------------------------


def test_the_rendered_review_opens_with_the_verdict_kept() -> None:
    refused = rendre_revue(revue("CHANGES_REQUESTED", ("bug", 90)), 80)
    kept = rendre_revue(revue("CHANGES_REQUESTED", ("doute", 40)), 80)

    assert refused.splitlines()[0] == "CHANGES_REQUESTED"
    assert kept.splitlines()[0] == "APPROVED"


def test_the_rendered_review_lists_remarks_then_the_summary() -> None:
    answer = revue(
        "CHANGES_REQUESTED",
        ("Le cas vide n'est pas géré.", 92),
        summary="Le reste est propre.",
        suggestions=["Renommer `x`."],
    )
    answer["blocking"][0]["location"] = "a.py:42"

    text = rendre_revue(answer, 80)

    assert "1. Le cas vide n'est pas géré. (a.py:42) [confiance: 92]" in text
    assert text.index("Le cas vide") < text.index("Le reste est propre.")
    assert "- Renommer `x`." in text


def test_the_rendered_review_of_an_absent_answer_says_why() -> None:
    text = rendre_revue(None, 80)

    assert text.splitlines()[0] == "CHANGES_REQUESTED"
    assert "absente" in text


def test_the_rendered_review_defaults_to_the_configured_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    answer = revue("CHANGES_REQUESTED", ("doute", 60))
    monkeypatch.setattr(settings, "reviewer_confidence_threshold", 50)
    assert rendre_revue(answer).splitlines()[0] == "CHANGES_REQUESTED"
    monkeypatch.setattr(settings, "reviewer_confidence_threshold", 70)
    assert rendre_revue(answer).splitlines()[0] == "APPROVED"


def test_confidence_threshold_defaults_to_80() -> None:
    assert Settings().reviewer_confidence_threshold == 80


def test_the_schema_requires_the_three_fields_and_avoids_bounds() -> None:
    item = REVIEWER_SCHEMA["properties"]["blocking"]["items"]

    assert REVIEWER_SCHEMA["required"] == ["verdict", "summary", "blocking"]
    assert item["required"] == ["text", "confidence"]
    assert "minimum" not in str(REVIEWER_SCHEMA)
    assert "maximum" not in str(REVIEWER_SCHEMA)


# ------------------------------------------------------------------
# L'étape du pipeline
# ------------------------------------------------------------------


class _ReviewerRunner:
    """Reviewer answers with `content` and `structured`; records the schema it gets."""

    def __init__(self, content: str, structured: dict[str, Any] | None) -> None:
        self._content = content
        self._structured = structured
        self.reviewer_schemas: list[object] = []

    async def run(self, **kwargs: object) -> AgentResult:
        role = kwargs["role"]
        is_reviewer = role == AgentRole.reviewer
        if is_reviewer:
            self.reviewer_schemas.append(kwargs.get("schema"))
        return AgentResult(
            role=role,  # type: ignore[arg-type]
            ticket_id="ticket-001",
            content=self._content if is_reviewer else "prose du codeur",
            structured=self._structured if is_reviewer else None,
            suggested_status=TicketStatus.in_review,
            duration_ms=1,
        )


async def _run(
    tmp_path: Path, runner: _ReviewerRunner
) -> tuple[bool, list[OrchestratorEvent]]:
    events: list[OrchestratorEvent] = []

    async def on_event(event: OrchestratorEvent) -> None:
        events.append(event)

    orch = _make_orchestrator(tmp_path, runner=runner, max_review_rounds=1)  # type: ignore[arg-type]
    result = await orch.run_pipeline("proj", "ticket-001", on_event)
    return result.approved, events


def _reviewer_done(events: list[OrchestratorEvent]) -> OrchestratorEvent:
    done = [
        e for e in events
        if e.type == EventType.AGENT_DONE and e.agent == AgentRole.reviewer
    ]
    assert len(done) == 1
    return done[0]


async def test_a_text_approval_without_structured_output_refuses(tmp_path: Path) -> None:
    runner = _ReviewerRunner("APPROVED", None)

    approved, events = await _run(tmp_path, runner)

    assert approved is False
    assert _reviewer_done(events).data["verdict"] == "CHANGES_REQUESTED"


async def test_an_off_schema_answer_refuses_whatever_the_text_says(
    tmp_path: Path,
) -> None:
    runner = _ReviewerRunner("APPROVED", {"verdict": "APPROVED"})

    approved, _ = await _run(tmp_path, runner)

    assert approved is False


async def test_the_reviewer_is_asked_for_the_schema(tmp_path: Path) -> None:
    runner = _ReviewerRunner("", revue("APPROVED"))

    await _run(tmp_path, runner)

    assert runner.reviewer_schemas == [REVIEWER_SCHEMA]


async def test_agent_done_carries_the_verdict_kept_after_the_threshold(
    tmp_path: Path,
) -> None:
    # Ticket-574 : un CHANGES_REQUESTED dont toutes les remarques sont sous le
    # seuil est une approbation avec remarques — et l'événement le dit.
    structured = revue("CHANGES_REQUESTED", ("doute", settings.reviewer_confidence_threshold - 1))
    runner = _ReviewerRunner("CHANGES_REQUESTED", structured)

    approved, events = await _run(tmp_path, runner)

    data = _reviewer_done(events).data
    assert approved is True
    assert data["verdict"] == "APPROVED"
    assert str(data["content"]).splitlines()[0] == "APPROVED"
    assert "doute" in str(data["content"])


async def test_agent_done_of_a_refusal_carries_the_rendered_review(
    tmp_path: Path,
) -> None:
    structured = revue("CHANGES_REQUESTED", ("bug réel", 95), summary="À reprendre.")
    runner = _ReviewerRunner("texte brut ignoré", structured)

    approved, events = await _run(tmp_path, runner)

    data = _reviewer_done(events).data
    assert approved is False
    assert data["verdict"] == "CHANGES_REQUESTED"
    assert "bug réel" in str(data["content"])
    assert "texte brut ignoré" not in str(data["content"])


async def test_the_threshold_comes_from_the_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "reviewer_confidence_threshold", 50)
    refused, _ = await _run(
        tmp_path, _ReviewerRunner("", revue("CHANGES_REQUESTED", ("doute", 60)))
    )
    approved, _ = await _run(
        tmp_path, _ReviewerRunner("", revue("CHANGES_REQUESTED", ("doute", 40)))
    )

    assert refused is False
    assert approved is True


# ------------------------------------------------------------------
# Le parseur par mot-clé a disparu, le prompt ne le demande plus
# ------------------------------------------------------------------


def test_the_keyword_parser_is_gone_from_the_backend() -> None:
    gone = re.compile(
        r"_parse_reviewer_verdict|_read_reviewer_verdict|_verdict_line"
        r"|reviewer_confidence(?!_threshold)"
    )
    found = [
        str(p.relative_to(SRC))
        for p in SRC.rglob("*.py")
        if gone.search(p.read_text(encoding="utf-8"))
    ]

    assert found == []


def test_the_reviewer_prompt_no_longer_asks_for_a_verdict_line() -> None:
    text = PROMPT.read_text(encoding="utf-8")
    lines = [line.strip() for line in text.splitlines()]

    assert "APPROVED" not in lines
    assert "CHANGES_REQUESTED" not in lines
    assert "[confiance:" not in text
    assert "verdict en première ligne" not in text


def test_the_reviewer_prompt_says_what_confidence_measures() -> None:
    text = PROMPT.read_text(encoding="utf-8")

    assert "confidence" in text
    assert "probabilité" in text
    assert "100" in text
    assert "seuil" in text
    assert "ne bloque" in text
