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
# Même borne que l'audit sécurité : à 8 000 caractères, un diff de branche
# reprise rendait la plupart des critères invérifiables (ticket-221).
_CODE_MAX_CHARS = 120_000

Verdict = Literal["APPROVED", "CHANGES_REQUESTED"]

_CHECKBOX_PREFIX = re.compile(r"^\s*-?\s*\[[ xX]?\]\s*")
_QUOTES_AND_TICKS = re.compile(r'[`"\'«»“”‘’]')
_PUNCTUATION_TAIL = re.compile(r"[.,;:!?]+$")
_MULTI_SPACE = re.compile(r"\s+")


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
        # Le modèle vient du manifeste du projet quand il déclare ce rôle
        # (ticket-188) ; sinon le défaut d'avant, rien ne change.
        self._model = model or _MODEL

    async def validate(
        self,
        criteria: list[str],
        code_produced: str,
        test_result: "TestResult | None",
    ) -> ValidationResult:
        if not criteria:
            return ValidationResult(
                all_passed=True,
                criteria=[],
                verdict="APPROVED",
                feedback="Aucun critère d'acceptation — approbation automatique.",
            )

        system_prompt = self._load_system_prompt()
        user_message = self._build_user_message(criteria, code_produced, test_result)

        try:
            result = await self._provider.complete(
                system=system_prompt,
                user=user_message,
                model=self._model,
                max_tokens=_MAX_TOKENS,
            )
        except Exception as exc:
            # Même régime que le JSON illisible : une validation qui n'a pas
            # eu lieu n'approuve rien (ticket-122).
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
    ) -> str:
        # Numérotation des critères pour que le LLM puisse rendre un `index`
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
        return (
            f"## Critères d'acceptation\n{criteria_block}\n\n"
            f"## Code produit\n{code_produced[:_CODE_MAX_CHARS]}"
            + test_block
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

        # Le verdict se recalcule depuis les critères réconciliés ; le champ
        # "verdict" du LLM est informatif mais ne pilote plus rien.
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
    prefix = f"{unjudged} critère(s) absent(s) de la réponse du validateur. "
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
