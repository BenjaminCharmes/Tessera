"""Tests for ValidatorService (ticket-036)."""

import json
from pathlib import Path

import pytest

from tests.test_providers_base import FakeProvider
from tessera.services.test_runner import TestResult
from tessera.services.validator import (
    CriterionResult,
    ValidationResult,
    ValidatorService,
)


@pytest.fixture
def provider() -> FakeProvider:
    return FakeProvider()


@pytest.fixture
def service(provider: FakeProvider) -> ValidatorService:
    return ValidatorService(provider, Path("agents/prompts"))


def _set_response(provider: FakeProvider, data: dict) -> None:
    provider.set_content(json.dumps(data))


class TestValidatorService:
    async def test_approved_when_all_criteria_pass(
        self, service: ValidatorService, provider: FakeProvider
    ) -> None:
        _set_response(
            provider,
            {
                "all_passed": True,
                "criteria": [{"criterion": "API returns 200", "passed": True, "note": ""}],
                "verdict": "APPROVED",
                "feedback": "All good.",
            },
        )

        result = await service.validate(
            criteria=["API returns 200"],
            code_produced="def get(): return 200",
            test_result=None,
        )

        assert result.verdict == "APPROVED"
        assert result.all_passed is True
        assert len(result.criteria) == 1
        assert result.criteria[0].passed is True

    async def test_changes_requested_when_criterion_fails(
        self, service: ValidatorService, provider: FakeProvider
    ) -> None:
        _set_response(
            provider,
            {
                "all_passed": False,
                "criteria": [
                    {"criterion": "DB persisted", "passed": False, "note": "Only in memory"}
                ],
                "verdict": "CHANGES_REQUESTED",
                "feedback": "Session not persisted.",
            },
        )

        result = await service.validate(
            criteria=["DB persisted"],
            code_produced="session = {}",
            test_result=None,
        )

        assert result.verdict == "CHANGES_REQUESTED"
        assert result.all_passed is False
        assert result.criteria[0].passed is False
        assert result.criteria[0].note == "Only in memory"

    async def test_auto_approved_when_no_criteria(
        self, service: ValidatorService, provider: FakeProvider
    ) -> None:
        result = await service.validate(
            criteria=[],
            code_produced="some code",
            test_result=None,
        )

        assert provider.calls == []
        assert result.verdict == "APPROVED"
        assert result.all_passed is True
        assert result.criteria == []

    async def test_includes_test_result_in_context(
        self, service: ValidatorService, provider: FakeProvider
    ) -> None:
        _set_response(
            provider,
            {
                "all_passed": True,
                "criteria": [{"criterion": "tests pass", "passed": True, "note": ""}],
                "verdict": "APPROVED",
                "feedback": "OK",
            },
        )
        test_result = TestResult(
            passed=True, total=5, failed=0, output_summary="5 passed", errors=[], duration_ms=100
        )

        await service.validate(
            criteria=["tests pass"],
            code_produced="def foo(): pass",
            test_result=test_result,
        )

        assert len(provider.calls) == 1
        assert "5 passed" in provider.calls[0]["user"]

    async def test_changes_requested_on_invalid_json_response(
        self, service: ValidatorService, provider: FakeProvider
    ) -> None:
        _set_response(provider, {})
        # empty dict — no verdict/all_passed keys
        result = await service.validate(
            criteria=["something"],
            code_produced="code",
            test_result=None,
        )
        assert result.verdict == "CHANGES_REQUESTED"

    async def test_multiple_criteria_all_pass(
        self, service: ValidatorService, provider: FakeProvider
    ) -> None:
        criteria = ["Returns 200", "Writes to DB", "Sends email"]
        _set_response(
            provider,
            {
                "all_passed": True,
                "criteria": [
                    {"criterion": c, "passed": True, "note": ""} for c in criteria
                ],
                "verdict": "APPROVED",
                "feedback": "All criteria satisfied.",
            },
        )

        result = await service.validate(
            criteria=criteria,
            code_produced="full implementation",
            test_result=None,
        )

        assert result.verdict == "APPROVED"
        assert len(result.criteria) == 3

    async def test_calls_provider_with_expected_shape(
        self, service: ValidatorService, provider: FakeProvider
    ) -> None:
        _set_response(
            provider,
            {
                "all_passed": True,
                "criteria": [],
                "verdict": "APPROVED",
                "feedback": "ok",
            },
        )

        await service.validate(
            criteria=["Returns 200"],
            code_produced="def get(): return 200",
            test_result=None,
        )

        assert len(provider.calls) == 1
        call = provider.calls[0]
        assert call["mode"] == "complete"
        assert isinstance(call["system"], str)
        assert "Returns 200" in call["user"]
        assert "def get(): return 200" in call["user"]
        # Dix critères avec une `note` chacun tiennent mal dans 1 024 tokens :
        # le JSON était tronqué, donc « non parseable », donc CHANGES_REQUESTED
        # pour une raison qui n'avait rien à voir avec le code (ticket-126).
        assert call["max_tokens"] >= 2048

    async def test_changes_requested_quand_le_provider_est_indisponible(
        self, service: ValidatorService
    ) -> None:
        # Le validateur rendait CHANGES_REQUESTED sur un JSON illisible mais
        # APPROVED sur un provider en panne : deux pannes, deux verdicts
        # opposés. Une validation qui n'a pas eu lieu n'approuve rien
        # (ticket-122).
        class _FailingProvider(FakeProvider):
            async def complete(self, **kwargs):  # type: ignore[override]
                raise Exception("Network error")

        service_with_failure = ValidatorService(_FailingProvider(), Path("agents/prompts"))

        result = await service_with_failure.validate(
            criteria=["something"],
            code_produced="code",
            test_result=None,
        )

        assert result.verdict == "CHANGES_REQUESTED"
        assert result.all_passed is False
        assert "Network error" in result.feedback


class TestCriteriaReconciliation:
    """Tests for criterion-level reconciliation (ticket-209)."""

    async def test_missing_criterion_causes_changes_requested(
        self, service: ValidatorService, provider: FakeProvider
    ) -> None:
        # 3 critères envoyés, 2 jugés true dans la réponse → CHANGES_REQUESTED
        # et le troisième figure en passed: false
        _set_response(
            provider,
            {
                "all_passed": True,
                "criteria": [
                    {"criterion": "Returns 200", "passed": True, "note": ""},
                    {"criterion": "Writes to DB", "passed": True, "note": ""},
                    # "Sends email" est absent de la réponse LLM
                ],
                "verdict": "APPROVED",
                "feedback": "Two criteria checked.",
            },
        )

        result = await service.validate(
            criteria=["Returns 200", "Writes to DB", "Sends email"],
            code_produced="code",
            test_result=None,
        )

        assert result.verdict == "CHANGES_REQUESTED"
        assert result.all_passed is False
        assert len(result.criteria) == 3
        missing = next(c for c in result.criteria if "email" in c.criterion.lower())
        assert missing.passed is False
        assert "non jugé" in missing.note

    async def test_llm_approved_verdict_ignored_when_criterion_fails(
        self, service: ValidatorService, provider: FakeProvider
    ) -> None:
        # Le champ "verdict" du LLM dit APPROVED mais un critère est passed: false
        _set_response(
            provider,
            {
                "all_passed": False,
                "criteria": [
                    {"criterion": "PR merged", "passed": False, "note": "PR still open"},
                    {"criterion": "Tests pass", "passed": True, "note": ""},
                ],
                "verdict": "APPROVED",
                "feedback": "Mostly good.",
            },
        )

        result = await service.validate(
            criteria=["PR merged", "Tests pass"],
            code_produced="code",
            test_result=None,
        )

        assert result.verdict == "CHANGES_REQUESTED"
        assert result.all_passed is False

    async def test_all_criteria_judged_true_gives_approved(
        self, service: ValidatorService, provider: FakeProvider
    ) -> None:
        # Non-régression : tous les critères jugés true → APPROVED
        _set_response(
            provider,
            {
                "all_passed": True,
                "criteria": [
                    {"criterion": "Feature implemented", "passed": True, "note": ""},
                    {"criterion": "Tests written", "passed": True, "note": ""},
                ],
                "verdict": "APPROVED",
                "feedback": "All good.",
            },
        )

        result = await service.validate(
            criteria=["Feature implemented", "Tests written"],
            code_produced="code",
            test_result=None,
        )

        assert result.verdict == "APPROVED"
        assert result.all_passed is True
        assert all(c.passed for c in result.criteria)

    async def test_checkbox_prefix_normalized_for_matching(
        self, service: ValidatorService, provider: FakeProvider
    ) -> None:
        # Les critères du ticket arrivent avec "- [ ]" ; le LLM répond sans
        _set_response(
            provider,
            {
                "all_passed": True,
                "criteria": [
                    {"criterion": "Tests pass", "passed": True, "note": ""},
                ],
                "verdict": "APPROVED",
                "feedback": "ok",
            },
        )

        result = await service.validate(
            criteria=["- [ ] Tests pass"],
            code_produced="code",
            test_result=None,
        )

        assert result.verdict == "APPROVED"
        assert result.criteria[0].passed is True


class TestValidationResult:
    def test_dataclass_fields(self) -> None:
        cr = CriterionResult(criterion="x", passed=True, note="")
        vr = ValidationResult(
            all_passed=True,
            criteria=[cr],
            verdict="APPROVED",
            feedback="ok",
        )
        assert vr.all_passed is True
        assert vr.verdict == "APPROVED"


async def test_a_whole_branch_diff_reaches_the_validator_intact(
    service: ValidatorService, provider: FakeProvider
) -> None:
    # ticket-221 : coupé à 8 000 caractères, le validateur déclarait
    # invérifiables des critères que la fin du diff satisfaisait.
    _set_response(
        provider,
        {"criteria": [{"criterion": "Returns 200", "passed": True, "note": ""}]},
    )
    diff = "+x = 1\n" * 10_000 + "+SENTINELLE_FIN_DU_DIFF\n"

    await service.validate(criteria=["Returns 200"], code_produced=diff, test_result=None)

    assert "SENTINELLE_FIN_DU_DIFF" in provider.calls[0]["user"]
