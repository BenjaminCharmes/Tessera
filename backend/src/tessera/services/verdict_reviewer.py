"""Reads the reviewer's structured answer: verdict, reason and rendered review.

Pure functions, no provider. The verdict comes from the validated object and
never from free text (ADR-061): an absent, off-schema or contradictory answer
refuses, as the other fail-closed gates do (ADR-039).
"""
from typing import Any

from tessera.config import settings
from tessera.models.agent import AgentResult
from tessera.services.reviewer_schema import VERDICTS

_REQUIRED: tuple[str, ...] = ("verdict", "summary", "blocking")
_ABSENT = "Sortie structurée du reviewer absente : verdict non lu."
_NO_REMARK = "CHANGES_REQUESTED sans aucune remarque bloquante."


def _remark_cause(remark: Any, index: int) -> str | None:
    """Why one entry of `blocking` is unusable, or None when it is valid."""
    label = f"blocking[{index}]"
    if not isinstance(remark, dict):
        return f"{label} n'est pas un objet"
    if not isinstance(remark.get("text"), str):
        return f"{label} : champ requis `text` absent ou hors schéma"
    confidence = remark.get("confidence")
    # `bool` est un `int` en Python : `true` n'est pas un score.
    if isinstance(confidence, bool) or not isinstance(confidence, int):
        return f"{label} : champ requis `confidence` absent ou non entier"
    if not 0 <= confidence <= 100:
        return f"{label} : `confidence` hors de 0-100 ({confidence})"
    if "location" in remark and not isinstance(remark["location"], str):
        return f"{label} : `location` n'est pas une chaîne"
    return None


def _invalid_cause(structured: dict[str, Any]) -> str | None:
    """Why the object is off-schema, or None when it can be read."""
    for field in _REQUIRED:
        if field not in structured:
            return f"champ requis absent : {field}"
    if structured["verdict"] not in VERDICTS:
        return f"`verdict` hors de l'énumération : {structured['verdict']!r}"
    if not isinstance(structured["summary"], str):
        return "`summary` n'est pas une chaîne"
    blocking = structured["blocking"]
    if not isinstance(blocking, list):
        return "`blocking` n'est pas une liste"
    for index, remark in enumerate(blocking):
        cause = _remark_cause(remark, index)
        if cause is not None:
            return cause
    suggestions = structured.get("suggestions", [])
    if not isinstance(suggestions, list) or not all(isinstance(s, str) for s in suggestions):
        return "`suggestions` n'est pas une liste de chaînes"
    return None


def _remark_line(position: int, remark: dict[str, Any]) -> str:
    """One numbered remark: text, location when given, confidence."""
    location = f" ({remark['location']})" if remark.get("location") else ""
    return f"{position}. {remark['text']}{location} [confiance: {remark['confidence']}]"


def _remark_lines(remarks: list[dict[str, Any]]) -> str:
    return "\n".join(_remark_line(i, r) for i, r in enumerate(remarks, start=1))


def lire_verdict(structured: dict[str, Any] | None, seuil: int) -> tuple[bool, str]:
    """Returns (approved, reason) from the reviewer's structured answer.

    A `CHANGES_REQUESTED` whose remarks are all under `seuil` reads as an
    approval with remarks (ticket-574); a threshold of 0 keeps every remark
    blocking. `APPROVED` with a remark at or over the threshold contradicts
    itself and refuses.
    """
    if structured is None:
        return False, _ABSENT
    cause = _invalid_cause(structured)
    if cause is not None:
        return False, f"Sortie du reviewer hors schéma : {cause}."
    blocking: list[dict[str, Any]] = structured["blocking"]
    above = [r for r in blocking if r["confidence"] >= seuil]
    if structured["verdict"] == "APPROVED":
        if above:
            return False, f"Contradiction : APPROVED avec des remarques bloquantes.\n{_remark_lines(above)}"
        return True, ""
    if not blocking:
        return False, structured["summary"] or _NO_REMARK
    if above:
        return False, "\n\n".join(p for p in (_remark_lines(above), structured["summary"]) if p)
    return True, ""


def rendre_revue(structured: dict[str, Any] | None, seuil: int | None = None) -> str:
    """The review as Markdown, for the coder and the screen.

    The first line is the verdict kept after the threshold, then the remarks,
    then the summary — the interface still reads that line (ticket-615 moves
    it to the event field).
    """
    limit = settings.reviewer_confidence_threshold if seuil is None else seuil
    approved, reason = lire_verdict(structured, limit)
    head = "APPROVED" if approved else "CHANGES_REQUESTED"
    if structured is None or _invalid_cause(structured) is not None:
        return f"{head}\n\n{reason}"
    parts = [head]
    if structured["blocking"]:
        parts.append("## Remarques\n" + _remark_lines(structured["blocking"]))
    if structured["summary"]:
        parts.append("## Résumé\n" + structured["summary"])
    suggestions: list[str] = structured.get("suggestions", [])
    if suggestions:
        parts.append("## Suggestions\n" + "\n".join(f"- {s}" for s in suggestions))
    return "\n\n".join(parts)


def juger_revue(structured: dict[str, Any] | None) -> tuple[bool, str, str]:
    """Read one reviewer answer at the configured threshold (ADR-061).

    Returns (approved, reason, rendered review). The verdict never comes from
    free text: this is the single reading the pipeline stage uses.
    """
    limit = settings.reviewer_confidence_threshold
    approved, reason = lire_verdict(structured, limit)
    return approved, reason, rendre_revue(structured, limit)


def donnees_fin_de_revue(
    approved: bool, review_text: str, result: AgentResult
) -> dict[str, Any]:
    """Payload of the reviewer's `AGENT_DONE` event: kept verdict and review."""
    return {
        "content": review_text,
        "verdict": "APPROVED" if approved else "CHANGES_REQUESTED",
        "cost_usd": result.cost_usd,
        "duration_ms": result.duration_ms,
    }
