"""Confidence scores on reviewer remarks — ticket-574, read from the structured field (ticket-614)."""
from typing import Any

from tessera.config import settings
from tessera.services.verdict_reviewer import lire_verdict
from tests.revue_structuree import revue


def _answer(*scores: int, suggestion: str = "") -> dict[str, Any]:
    return revue(
        "CHANGES_REQUESTED",
        *((f"Problème {i} dans a.py", score) for i, score in enumerate(scores, start=1)),
        summary="Le reste est bon.",
        suggestions=[suggestion] if suggestion else None,
    )


def test_all_scores_below_threshold_reads_as_approval() -> None:
    assert lire_verdict(_answer(40, 79), 80) == (True, "")


def test_one_score_above_threshold_keeps_changes_requested() -> None:
    approved, reason = lire_verdict(_answer(30, 90, 50), 80)

    assert approved is False
    assert "Problème 2" in reason


def test_score_equal_to_threshold_blocks() -> None:
    assert lire_verdict(_answer(80), 80)[0] is False


def test_one_missing_score_among_low_ones_keeps_refusal() -> None:
    answer = _answer(10, 10, 20)
    del answer["blocking"][1]["confidence"]

    assert lire_verdict(answer, 80)[0] is False


def test_zero_threshold_disables_the_filter() -> None:
    assert lire_verdict(_answer(10), 0)[0] is False


def test_suggestions_never_count_as_blocking() -> None:
    answer = _answer(95, suggestion="Détail à reprendre (confiance : 20)")

    assert lire_verdict(answer, 80)[0] is False


def test_without_remark_the_filter_has_nothing_to_lower() -> None:
    assert lire_verdict(_answer(), 80)[0] is False


def test_approved_answer_is_untouched() -> None:
    assert lire_verdict(revue("APPROVED", summary="Tout."), 80) == (True, "")


def test_the_configured_threshold_is_the_one_the_pipeline_reads() -> None:
    # Le pipeline passe `settings.reviewer_confidence_threshold` à `lire_verdict`.
    score = settings.reviewer_confidence_threshold - 1

    assert lire_verdict(_answer(score), settings.reviewer_confidence_threshold) == (True, "")
