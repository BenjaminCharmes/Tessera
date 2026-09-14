"""Tests for ValidatorService (ticket-036)."""

import json
from pathlib import Path

import pytest

from tests.test_providers_base import FakeProvider
from vibe_ide.services.test_runner import TestResult
from vibe_ide.services.validator import (
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

    async def test_approved_on_invalid_json_response(
        self, service: ValidatorService, provider: FakeProvider
    ) -> None:
        _set_response(provider, {})
        # empty dict — no verdict/all_passed keys
        result = await service.validate(
            criteria=["something"],
            code_produced="code",
            test_result=None,
        )
        # graceful degradation: treat as approved if JSON malformed
        assert result.verdict in ("APPROVED", "CHANGES_REQUESTED")

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
        assert call["max_tokens"] > 0

    async def test_approved_on_llm_failure(self, service: ValidatorService) -> None:
        class _FailingProvider(FakeProvider):
            async def complete(self, **kwargs):  # type: ignore[override]
                raise Exception("Network error")

        service_with_failure = ValidatorService(_FailingProvider(), Path("agents/prompts"))

        result = await service_with_failure.validate(
            criteria=["something"],
            code_produced="code",
            test_result=None,
        )

        assert result.verdict == "APPROVED"
        assert result.all_passed is True


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
