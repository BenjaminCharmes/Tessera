import re
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
_MAX_TOKENS = 2048
_PROMPT_FILE = "validateur.md"
# Même borne que l'audit sécurité : à 8 000 caractères, un diff de branche
# reprise rendait la plupart des critères invérifiables (ticket-221).
_CODE_MAX_CHARS = 120_000

Verdict = Literal["APPROVED", "CHANGES_REQUESTED"]

_CHECKBOX_PREFIX = re.compile(r"^\s*-?\s*\[[ xX]?\]\s*")


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

        raw_criteria = [
            CriterionResult(
                criterion=str(c.get("criterion", "")),
                passed=bool(c.get("passed", False)),
                note=str(c.get("note", "")),
            )
            for c in parsed.get("criteria", [])
            if isinstance(c, dict)
        ]

        # Rapprochement par texte normalisé : chaque critère envoyé doit
        # figurer dans la réponse avec passed: true pour que la validation
        # soit approuvée. Un critère absent de la réponse LLM est ajouté en
        # passed: false (ADR-039).
        response_by_norm = {_normalize(c.criterion): c for c in raw_criteria}
        criteria: list[CriterionResult] = []
        for sent in sent_criteria:
            norm = _normalize(sent)
            if norm in response_by_norm:
                criteria.append(response_by_norm[norm])
            else:
                criteria.append(
                    CriterionResult(
                        criterion=sent,
                        passed=False,
                        note="non jugé par le validateur",
                    )
                )

        # Le verdict se recalcule depuis les critères réconciliés ; le champ
        # "verdict" du LLM est informatif mais ne pilote plus rien.
        all_passed = all(c.passed for c in criteria) if criteria else True
        verdict: Verdict = "APPROVED" if all_passed else "CHANGES_REQUESTED"

        return ValidationResult(
            all_passed=all_passed,
            criteria=criteria,
            verdict=verdict,
            feedback=str(parsed.get("feedback", "")),
        )


def _normalize(text: str) -> str:
    """Normalize a criterion text for matching: strip checkboxes and lowercase."""
    text = _CHECKBOX_PREFIX.sub("", text.strip())
    return text.lower().strip()
