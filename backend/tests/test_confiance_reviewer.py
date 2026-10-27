"""Confidence scores on reviewer remarks — ticket-574."""
from pathlib import Path

import pytest

from tessera.config import Settings, settings
from tessera.services.pipeline_text import _parse_reviewer_verdict, _read_reviewer_verdict
from tessera.services.reviewer_confidence import all_blocking_remarks_below

PROMPT = Path(__file__).resolve().parents[2] / "agents" / "prompts" / "reviewer.md"


def _answer(*scores: str, suggestion: str = "") -> str:
    remarks = "\n".join(
        f"{i}. Problème {i} dans a.py [confiance: {score}]" if score else f"{i}. Problème {i}"
        for i, score in enumerate(scores, start=1)
    )
    return (
        f"CHANGES_REQUESTED\n\n## Problèmes bloquants\n{remarks}\n\n"
        f"## Ce qui est bien (à garder)\nLe reste.\n\n"
        f"## Suggestions non bloquantes\n{suggestion}"
    )


def test_all_scores_below_threshold_reads_as_approval() -> None:
    approved, reason = _parse_reviewer_verdict(_answer("40", "79"), 80)
    assert approved is True
    assert reason == ""


def test_one_score_above_threshold_keeps_changes_requested() -> None:
    approved, reason = _parse_reviewer_verdict(_answer("30", "90", "50"), 80)
    assert approved is False
    assert "Problème 2" in reason


def test_score_equal_to_threshold_blocks() -> None:
    approved, _ = _parse_reviewer_verdict(_answer("80"), 80)
    assert approved is False


def test_answer_without_score_behaves_as_before() -> None:
    content = _answer("", "")
    assert _parse_reviewer_verdict(content, 80) == _parse_reviewer_verdict(content)
    assert _parse_reviewer_verdict(content, 80)[0] is False


def test_one_missing_score_among_low_ones_keeps_refusal() -> None:
    approved, _ = _parse_reviewer_verdict(_answer("10", "", "20"), 80)
    assert approved is False


def test_no_threshold_ignores_scores() -> None:
    approved, _ = _parse_reviewer_verdict(_answer("10"))
    assert approved is False


def test_zero_threshold_disables_the_filter() -> None:
    approved, _ = _parse_reviewer_verdict(_answer("10"), 0)
    assert approved is False


def test_scores_outside_blocking_section_are_ignored() -> None:
    content = _answer("95", suggestion="1. Détail [confiance: 20]")
    assert _parse_reviewer_verdict(content, 80)[0] is False


def test_score_without_brackets_is_read() -> None:
    content = "CHANGES_REQUESTED\n\n## Problèmes bloquants\n1. Bug. Confiance : 35\n"
    assert _parse_reviewer_verdict(content, 80) == (True, "")


def test_section_missing_keeps_refusal() -> None:
    content = "CHANGES_REQUESTED\n\nUn problème [confiance: 10]"
    assert _parse_reviewer_verdict(content, 80)[0] is False


def test_approved_answer_is_untouched() -> None:
    assert _parse_reviewer_verdict("APPROVED\n\n## Ce qui est bien\nTout.", 80) == (True, "")


def test_extra_score_for_one_remark_keeps_refusal() -> None:
    content = (
        "CHANGES_REQUESTED\n\n## Problèmes bloquants\n"
        "1. Bug [confiance: 10] [confiance: 20]\n"
    )
    assert all_blocking_remarks_below(content, 80) is False


def test_read_reviewer_verdict_uses_the_configured_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "reviewer_confidence_threshold", 50)
    assert _read_reviewer_verdict(_answer("60")) == _parse_reviewer_verdict(_answer("60"))
    assert _read_reviewer_verdict(_answer("40")) == (True, "")


def test_confidence_threshold_defaults_to_80() -> None:
    assert Settings().reviewer_confidence_threshold == 80


def test_reviewer_prompt_asks_for_a_score_and_a_threshold() -> None:
    text = PROMPT.read_text(encoding="utf-8")
    assert "[confiance:" in text
    assert "100" in text
    assert "seuil" in text
    assert "ne bloque" in text
