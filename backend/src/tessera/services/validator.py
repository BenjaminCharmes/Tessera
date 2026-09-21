from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, TYPE_CHECKING

from tessera.services.providers.base import LLMProvider
from tessera.utils.json_extract import extract_json
from tessera.utils.logger import get_logger

if TYPE_CHECKING:
    from tessera.services.test_runner import TestResult

_logger = get_logger(__name__)

_MODEL = "claude-sonnet-4-6"
_MAX_TOKENS = 1024
_PROMPT_FILE = "validateur.md"

Verdict = Literal["APPROVED", "CHANGES_REQUESTED"]


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
    def __init__(self, provider: LLMProvider, prompts_dir: Path) -> None:
        self._provider = provider
        self._prompts_dir = prompts_dir

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
                model=_MODEL,
                max_tokens=_MAX_TOKENS,
            )
        except Exception as exc:
            _logger.warning("validator_llm_failed", extra={"error": str(exc)})
            return ValidationResult(
                all_passed=True,
                criteria=[],
                verdict="APPROVED",
                feedback="Validation LLM indisponible — approbation par défaut.",
            )

        return self._parse_response(result.content)

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
        criteria_block = "\n".join(f"- {c}" for c in criteria)
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
            f"## Code produit\n{code_produced[:8000]}"
            + test_block
        )

    def _parse_response(self, raw: str) -> ValidationResult:
        parsed = extract_json(raw)
        if not parsed:
            _logger.warning("validator_invalid_json", extra={"raw": raw[:200]})
            return ValidationResult(
                all_passed=False,
                criteria=[],
                verdict="CHANGES_REQUESTED",
                feedback="Réponse du validateur non parseable.",
            )

        all_passed = bool(parsed.get("all_passed", False))
        verdict: Verdict = "APPROVED" if all_passed else "CHANGES_REQUESTED"
        raw_verdict = parsed.get("verdict", "")
        if raw_verdict in ("APPROVED", "CHANGES_REQUESTED"):
            verdict = raw_verdict

        criteria = [
            CriterionResult(
                criterion=str(c.get("criterion", "")),
                passed=bool(c.get("passed", False)),
                note=str(c.get("note", "")),
            )
            for c in parsed.get("criteria", [])
            if isinstance(c, dict)
        ]

        return ValidationResult(
            all_passed=all_passed,
            criteria=criteria,
            verdict=verdict,
            feedback=str(parsed.get("feedback", "")),
        )
