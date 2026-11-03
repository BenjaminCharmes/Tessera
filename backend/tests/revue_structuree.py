"""Reviewer answers in their structured form, for the test doubles (ADR-061)."""
from typing import Any


def revue(
    verdict: str,
    *remarks: tuple[str, int],
    summary: str = "",
    suggestions: list[str] | None = None,
) -> dict[str, Any]:
    """A schema-valid reviewer answer; each remark is `(text, confidence)`."""
    answer: dict[str, Any] = {
        "verdict": verdict,
        "summary": summary,
        "blocking": [{"text": text, "confidence": conf} for text, conf in remarks],
    }
    if suggestions is not None:
        answer["suggestions"] = suggestions
    return answer


def revue_depuis_texte(content: str) -> dict[str, Any] | None:
    """The structured form of a double's short answer, or None for any other text.

    `APPROVED…` gives an approval; `CHANGES_REQUESTED: reason` gives a refusal
    with one remark, fully confident. Anything else stays unstructured, so a
    double that answers in prose is refused like a real one.
    """
    if content.startswith("APPROVED"):
        return revue("APPROVED", summary=content)
    if content.startswith("CHANGES_REQUESTED"):
        reason = content.split(":", 1)[1].strip() if ":" in content else content
        return revue("CHANGES_REQUESTED", (reason, 100))
    return None
