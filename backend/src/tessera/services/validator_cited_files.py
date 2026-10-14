# -*- coding: utf-8 -*-
"""Files cited by acceptance criteria, joined to the validator message.

Split out of ``validator.py`` (ticket-316, ticket-434): the section builder
now also returns a report of what was joined, so the pipeline log can say
what the validator actually received.
"""
import re
from dataclasses import dataclass, field
from pathlib import Path

# Max size of the cited-files section -- all entries combined.
# Beyond this the current file is truncated (ticket-316).
CITED_FILES_MAX_CHARS = 20_000
# Directories to skip during recursive search for a cited file.
_EXCLUDED_DIRS = {".venv", "node_modules", ".git", "__pycache__", "dist", "build"}

# Backtick-quoted content inside a criterion.
_BACKTICK_REF = re.compile(r"`([^`\n]+)`")
# Trailing line-number suffix, e.g. ":44" in "BillingTab.test.tsx:44".
_LINE_SUFFIX = re.compile(r":\d+$")
# Recognised file extension (1-6 letters).
_FILE_EXTENSION = re.compile(r"\.[a-zA-Z]{1,6}$")


@dataclass
class CitedFilesReport:
    """What the cited-files section holds, reference by reference."""

    # Every file found and read, truncated ones included.
    joined: list[str] = field(default_factory=list)
    # Subset of ``joined`` cut at the size limit.
    truncated: list[str] = field(default_factory=list)
    # References that match no file in the project.
    absent: list[str] = field(default_factory=list)
    # References left out because the budget was already spent.
    omitted: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not (self.joined or self.absent or self.omitted)


def extract_file_refs(criteria: list[str]) -> list[str]:
    """Extract file references from acceptance criteria.

    Picks up any backtick-quoted token that looks like a file path (has an
    extension), after stripping a trailing ``:N`` line-number suffix.
    Preserves insertion order and deduplicates.
    """
    seen: set[str] = set()
    refs: list[str] = []
    for criterion in criteria:
        for m in _BACKTICK_REF.finditer(criterion):
            candidate = _LINE_SUFFIX.sub("", m.group(1).strip())
            if _FILE_EXTENSION.search(candidate):
                if candidate not in seen:
                    seen.add(candidate)
                    refs.append(candidate)
    return refs


def _find_file_in_project(ref: str, project_root: Path) -> Path | None:
    """Resolve a file reference against the project root.

    Tries the reference as a relative path first, then falls back to a
    recursive search by filename, skipping common non-source directories.
    """
    # Un critère vient d'un ticket, qui peut venir d'une issue GitHub : sans
    # cette borne, `../../.env` ou un chemin absolu ferait joindre au message
    # du validateur un fichier hors du projet (audit sécurité du ticket-316).
    racine = project_root.resolve()

    def _dans_le_projet(chemin: Path) -> bool:
        try:
            chemin.resolve().relative_to(racine)
        except ValueError:
            return False
        return True

    if Path(ref).is_absolute():
        return None
    candidate = project_root / ref
    if candidate.is_file() and _dans_le_projet(candidate):
        return candidate
    name = Path(ref).name
    if not name or name in (".", ".."):
        return None
    for found in project_root.rglob(name):
        if any(part in _EXCLUDED_DIRS for part in found.parts):
            continue
        if found.is_file() and _dans_le_projet(found):
            return found
    return None


def _read_entry(
    ref: str, found: Path, budget: int, report: CitedFilesReport
) -> str:
    """Read one found file into a section entry, truncating at ``budget``."""
    raw = found.read_text(encoding="utf-8", errors="replace")
    report.joined.append(ref)
    if len(raw) > budget:
        report.truncated.append(ref)
        raw = raw[:budget] + f"\n[... {len(raw) - budget} caractères tronqués]"
    return f"### {ref}\n```\n{raw}\n```"


def build_cited_files_section(
    refs: list[str], project_root: Path
) -> tuple[str, CitedFilesReport]:
    """Build the cited-files section and the report of what it holds.

    Each referenced file is read and added up to ``CITED_FILES_MAX_CHARS``
    total. A file that does not fit is truncated with a mention; a file that
    does not exist is noted as absent; a reference met after the budget is
    spent is listed as not joined rather than dropped silently. Returns an
    empty section when there are no refs.
    """
    report = CitedFilesReport()
    if not refs:
        return "", report
    entries: list[str] = []
    budget = CITED_FILES_MAX_CHARS
    for ref in refs:
        if budget <= 0:
            report.omitted.append(ref)
            entries.append(f"### {ref}\n*(non joint : budget épuisé)*")
            continue
        found = _find_file_in_project(ref, project_root)
        if found is None:
            report.absent.append(ref)
            entry = f"### {ref}\n*(absent du dépôt)*"
        else:
            entry = _read_entry(ref, found, budget, report)
        budget -= len(entry)
        entries.append(entry)
    header = (
        "## Fichiers cités par les critères"
        " (tels qu'ils sont après le run)\n\n"
        "Un critère peut être satisfait par du code"
        " préexistant visible dans cette section.\n\n"
    )
    return "\n\n" + header + "\n\n".join(entries), report


def format_cited_files_log(report: CitedFilesReport) -> str:
    """One journal line: ``validateur: fichiers cités joints : a, b (tronqué) ; absents : c``.

    Returns an empty string when no file was cited.
    """
    if report.is_empty():
        return ""
    joined = ", ".join(
        f"{ref} (tronqué)" if ref in report.truncated else ref
        for ref in report.joined
    )
    segments = [f"fichiers cités joints : {joined or 'aucun'}"]
    if report.absent:
        segments.append("absents : " + ", ".join(report.absent))
    if report.omitted:
        segments.append("non joints (budget épuisé) : " + ", ".join(report.omitted))
    return "validateur: " + " ; ".join(segments)
