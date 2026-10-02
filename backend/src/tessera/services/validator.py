# -*- coding: utf-8 -*-
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, TYPE_CHECKING

from tessera.services.providers.base import LLMProvider
from tessera.utils.json_extract import extract_json
from tessera.utils.logger import get_logger

if TYPE_CHECKING:
    from tessera.services.test_runner import TestResult

_logger = get_logger(__name__)

_MODEL = "claude-sonnet-4-6"
_MAX_TOKENS = 2048
_PROMPT_FILE = "validateur.md"
# Same cap as the security audit: at 8 000 chars a branch diff made most
# criteria unverifiable (ticket-221).
_CODE_MAX_CHARS = 120_000
# Max size of the cited-files section -- all entries combined.
# Beyond this the current file is truncated (ticket-316).
_CITED_FILES_MAX_CHARS = 20_000
# Directories to skip during recursive search for a cited file.
_EXCLUDED_DIRS = {".venv", "node_modules", ".git", "__pycache__", "dist", "build"}

Verdict = Literal["APPROVED", "CHANGES_REQUESTED"]

_CHECKBOX_PREFIX = re.compile(r"^\s*-?\s*\[[ xX]?\]\s*")
# Matches backtick, ASCII quotes, guillemets and typographic curly quotes.
# \uXXXX escapes keep this file 100 % ASCII on disk (avoids cp1252/UTF-8 mix).
_QUOTES_AND_TICKS = re.compile(
    "[\x60\"'«»“”‘’]"
)
_PUNCTUATION_TAIL = re.compile(r"[.,;:!?]+$")
_MULTI_SPACE = re.compile(r"\s+")
# Backtick-quoted content inside a criterion.
_BACKTICK_REF = re.compile(r"`([^`\n]+)`")
# Trailing line-number suffix, e.g. ":44" in "BillingTab.test.tsx:44".
_LINE_SUFFIX = re.compile(r":\d+$")
# Recognised file extension (1-6 letters).
_FILE_EXTENSION = re.compile(r"\.[a-zA-Z]{1,6}$")


@dataclass
class CriterionResult:
    criterion: str
    passed: bool
    note: str = ""


@dataclass
class ValidationResult:
    all_passed: bool
    criteria: list[CriterionResult]
    verdict: Verdict
    feedback: str


class ValidatorService:
    def __init__(
        self, provider: LLMProvider, prompts_dir: Path, model: str | None = None
    ) -> None:
        self._provider = provider
        self._prompts_dir = prompts_dir
        # Model comes from the project manifest when it declares this role
        # (ticket-188); otherwise the previous default, nothing changes.
        self._model = model or _MODEL

    async def validate(
        self,
        criteria: list[str],
        code_produced: str,
        test_result: "TestResult | None",
        project_root: Path | None = None,
    ) -> ValidationResult:
        if not criteria:
            return ValidationResult(
                all_passed=True,
                criteria=[],
                verdict="APPROVED",
                feedback=(
                    "Aucun critère d'acceptation"
                    " — approbation automatique."
                ),
            )

        system_prompt = self._load_system_prompt()
        user_message = self._build_user_message(
            criteria, code_produced, test_result, project_root
        )

        try:
            result = await self._provider.complete(
                system=system_prompt,
                user=user_message,
                model=self._model,
                max_tokens=_MAX_TOKENS,
            )
        except Exception as exc:
            # Same policy as unreadable JSON: a validation that did not happen
            # must not approve anything (ticket-122).
            _logger.warning("validator_llm_failed", extra={"error": str(exc)})
            return ValidationResult(
                all_passed=False,
                criteria=[],
                verdict="CHANGES_REQUESTED",
                feedback=f"Validation indisponible : {exc}",
            )

        return self._parse_response(result.content, criteria)

    def _load_system_prompt(self) -> str:
        prompt_path = self._prompts_dir / _PROMPT_FILE
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")
        return "Validate acceptance criteria and respond with JSON."

    def _build_user_message(
        self,
        criteria: list[str],
        code_produced: str,
        test_result: "TestResult | None",
        project_root: Path | None = None,
    ) -> str:
        # Number the criteria so the LLM can return an `index`.
        criteria_block = "\n".join(
            f"{i}. {c}" for i, c in enumerate(criteria, start=1)
        )
        test_block = ""
        if test_result is not None:
            badge = "✅" if test_result.passed else "❌"
            test_block = (
                f"\n\n## Résultats des tests {badge}\n"
                f"{test_result.output_summary}\n"
                + (
                    "\nErreurs:\n" + "\n".join(test_result.errors[:3])
                    if test_result.errors
                    else ""
                )
            )
        cited_block = ""
        if project_root is not None:
            refs = extract_file_refs(criteria)
            cited_block = _build_cited_files_section(refs, project_root)
        return (
            f"## Critères d'acceptation\n{criteria_block}\n\n"
            f"## Code produit\n{code_produced[:_CODE_MAX_CHARS]}"
            + test_block
            + cited_block
        )

    def _parse_response(
        self, raw: str, sent_criteria: list[str]
    ) -> ValidationResult:
        parsed = extract_json(raw)
        if not parsed:
            _logger.warning("validator_invalid_json", extra={"raw": raw[:200]})
            return ValidationResult(
                all_passed=False,
                criteria=[],
                verdict="CHANGES_REQUESTED",
                feedback="Réponse du validateur non parseable.",
            )

        raw_entries = [c for c in parsed.get("criteria", []) if isinstance(c, dict)]
        index_map, tolerant_map = _build_criterion_lookups(raw_entries, len(sent_criteria))
        criteria = _reconcile_criteria(sent_criteria, index_map, tolerant_map)

        # Verdict is recomputed from reconciled criteria; the LLM "verdict"
        # field is informational only and no longer drives anything.
        all_passed = all(c.passed for c in criteria) if criteria else True
        verdict: Verdict = "APPROVED" if all_passed else "CHANGES_REQUESTED"
        feedback = _build_feedback(str(parsed.get("feedback", "")), criteria)

        return ValidationResult(
            all_passed=all_passed,
            criteria=criteria,
            verdict=verdict,
            feedback=feedback,
        )


def _build_criterion_lookups(
    raw_entries: list[dict[str, Any]],
    n_criteria: int,
) -> tuple[dict[int, CriterionResult], dict[str, CriterionResult]]:
    """Build index-based and tolerant-text-based lookup maps from LLM response entries."""
    index_map: dict[int, CriterionResult] = {}
    tolerant_map: dict[str, CriterionResult] = {}
    for entry in raw_entries:
        cr = CriterionResult(
            criterion=str(entry.get("criterion", "")),
            passed=bool(entry.get("passed", False)),
            note=str(entry.get("note", "")),
        )
        raw_idx = entry.get("index")
        if isinstance(raw_idx, int) and 1 <= raw_idx <= n_criteria:
            index_map[raw_idx] = cr
        norm = _tolerant_normalize(cr.criterion)
        if norm:
            tolerant_map[norm] = cr
    return index_map, tolerant_map


def _reconcile_criteria(
    sent_criteria: list[str],
    index_map: dict[int, CriterionResult],
    tolerant_map: dict[str, CriterionResult],
) -> list[CriterionResult]:
    """Match each sent criterion to an LLM response entry, by index then by text."""
    criteria: list[CriterionResult] = []
    for i, sent in enumerate(sent_criteria, start=1):
        matched: CriterionResult | None = index_map.get(i)
        if matched is None:
            matched = tolerant_map.get(_tolerant_normalize(sent))
        if matched is not None:
            criteria.append(matched)
        else:
            criteria.append(
                CriterionResult(
                    criterion=sent,
                    passed=False,
                    note="non jugé par le validateur",
                )
            )
    return criteria


def _build_feedback(base_feedback: str, criteria: list[CriterionResult]) -> str:
    """Prepend a warning to the feedback if any criterion was not judged."""
    unjudged = sum(1 for c in criteria if "non jugé" in c.note)
    if not unjudged:
        return base_feedback
    prefix = (
        f"{unjudged} critère(s) absent(s)"
        " de la réponse du validateur. "
    )
    return prefix + base_feedback


def _normalize(text: str) -> str:
    """Normalize a criterion text for matching: strip checkboxes and lowercase."""
    text = _CHECKBOX_PREFIX.sub("", text.strip())
    return text.lower().strip()


def _tolerant_normalize(text: str) -> str:
    """Normalize tolerantly: strip checkboxes, backticks, quotes, trailing punctuation."""
    text = _CHECKBOX_PREFIX.sub("", text.strip())
    text = _QUOTES_AND_TICKS.sub("", text)
    text = _PUNCTUATION_TAIL.sub("", text.strip())
    text = _MULTI_SPACE.sub(" ", text)
    return text.lower().strip()


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
    candidate = project_root / ref
    if candidate.exists() and candidate.is_file():
        return candidate
    name = Path(ref).name
    for found in project_root.rglob(name):
        if not any(part in _EXCLUDED_DIRS for part in found.parts):
            return found
    return None


def _build_cited_files_section(refs: list[str], project_root: Path) -> str:
    """Build the cited-files section to append to the validator message.

    Each referenced file is read and added up to ``_CITED_FILES_MAX_CHARS``
    total. A file that does not fit is truncated with a mention; a file that
    does not exist is noted as absent. Returns an empty string when no refs.
    """
    if not refs:
        return ""
    entries: list[str] = []
    budget = _CITED_FILES_MAX_CHARS
    for ref in refs:
        found = _find_file_in_project(ref, project_root)
        if found is None:
            entry = f"### {ref}\n*(absent du dépôt)*"
        else:
            raw = found.read_text(encoding="utf-8", errors="replace")
            if len(raw) > budget:
                omitted = len(raw) - budget
                raw = (
                    raw[:budget]
                    + f"\n[... {omitted} caractères tronqués]"
                )
            entry = f"### {ref}\n```\n{raw}\n```"
        budget -= len(entry)
        entries.append(entry)
        if budget <= 0:
            break
    header = (
        "## Fichiers cités par les critères"
        " (tels qu'ils sont après le run)\n\n"
        "Un critère peut être satisfait par du code"
        " préexistant visible dans cette section.\n\n"
    )
    return "\n\n" + header + "\n\n".join(entries)
