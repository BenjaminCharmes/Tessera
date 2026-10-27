"""Confidence scores on the reviewer's blocking remarks (ticket-574).

Pure text: reads the `## Problèmes bloquants` section of a reviewer answer
and decides whether every remark in it is below the confidence threshold.
Anything unclear — a remark without a score, an extra or missing score, no
section — answers "no", so the refusal stands (ADR-009, ADR-039).
"""
import re

_BLOCKING_HEADING = re.compile(r"^#{1,6}\s*probl[èe]mes\s+bloquants\b", re.IGNORECASE)
_ANY_HEADING = re.compile(r"^#{1,6}\s")
_REMARK_START = re.compile(r"^\s*(?:\d+[.)]|[-*])\s+\S")
_CONFIDENCE = re.compile(r"confiance\s*:\s*(\d{1,3})", re.IGNORECASE)


def _blocking_section(content: str) -> list[str]:
    """Lines of the blocking-problems section, heading excluded; empty when absent."""
    section: list[str] = []
    inside = False
    for line in content.splitlines():
        if inside and _ANY_HEADING.match(line):
            break
        if inside:
            section.append(line)
        elif _BLOCKING_HEADING.match(line.strip()):
            inside = True
    return section


def all_blocking_remarks_below(content: str, threshold: int) -> bool:
    """True when the section lists remarks and every one carries a score under `threshold`.

    A threshold of 0 or less disables the filter. The number of scores must
    equal the number of remarks: one missing, or one remark scored twice,
    keeps the refusal.
    """
    if threshold <= 0:
        return False
    section = _blocking_section(content)
    remarks = sum(1 for line in section if _REMARK_START.match(line))
    scores = [int(m) for m in _CONFIDENCE.findall("\n".join(section))]
    if remarks == 0 or len(scores) != remarks:
        return False
    return all(score < threshold for score in scores)
