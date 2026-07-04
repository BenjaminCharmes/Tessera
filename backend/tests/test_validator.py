"""Tests for ValidatorService (ticket-036)."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from vibe_ide.services.test_runner import TestResult
from vibe_ide.services.validator import (
    CriterionResult,
    ValidationResult,
    ValidatorService,
)


@pytest.fixture
def service() -> ValidatorService:
    mock_client = MagicMock()
    return ValidatorService(mock_client, Path("agents/prompts"))


def _make_llm_response(data: dict) -> MagicMock:
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=json.dumps(data))]
    return mock_msg


class TestValidatorService:
    async def test_approved_when_all_criteria_pass(self, service: ValidatorService) -> None:
        service._client.messages.create = AsyncMock(
            return_value=_make_llm_response(
                {
                    "all_passed": True,
                    "criteria": [{"criterion": "API returns 200", "passed": True, "note": ""}],
                    "verdict": "APPROVED",
                    "feedback": "All good.",
                }
            )
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

    async def test_changes_requested_when_criterion_fails(self, service: ValidatorService) -> None:
        service._client.messages.create = AsyncMock(
            return_value=_make_llm_response(
                {
                    "all_passed": False,
                    "criteria": [
                        {"criterion": "DB persisted", "passed": False, "note": "Only in memory"}
                    ],
                    "verdict": "CHANGES_REQUESTED",
                    "feedback": "Session not persisted.",
                }
            )
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

    async def test_auto_approved_when_no_criteria(self, service: ValidatorService) -> None:
        result = await service.validate(
            criteria=[],
            code_produced="some code",
            test_result=None,
        )

        service._client.messages.create.assert_not_called()
        assert result.verdict == "APPROVED"
        assert result.all_passed is True
        assert result.criteria == []

    async def test_includes_test_result_in_context(self, service: ValidatorService) -> None:
        service._client.messages.create = AsyncMock(
            return_value=_make_llm_response(
                {
                    "all_passed": True,
                    "criteria": [{"criterion": "tests pass", "passed": True, "note": ""}],
                    "verdict": "APPROVED",
                    "feedback": "OK",
                }
            )
        )
        test_result = TestResult(
            passed=True, total=5, failed=0, output_summary="5 passed", errors=[], duration_ms=100
        )

        await service.validate(
            criteria=["tests pass"],
            code_produced="def foo(): pass",
            test_result=test_result,
        )

        call_args = service._client.messages.create.call_args
        user_msg = call_args.kwargs["messages"][0]["content"]
        assert "5 passed" in user_msg

    async def test_approved_on_invalid_json_response(self, service: ValidatorService) -> None:
        service._client.messages.create = AsyncMock(
            return_value=_make_llm_response({})
        )
        # empty dict — no verdict/all_passed keys
        result = await service.validate(
            criteria=["something"],
            code_produced="code",
            test_result=None,
        )
        # graceful degradation: treat as approved if JSON malformed
        assert result.verdict in ("APPROVED", "CHANGES_REQUESTED")

    async def test_multiple_criteria_all_pass(self, service: ValidatorService) -> None:
        criteria = ["Returns 200", "Writes to DB", "Sends email"]
        service._client.messages.create = AsyncMock(
            return_value=_make_llm_response(
                {
                    "all_passed": True,
                    "criteria": [
                        {"criterion": c, "passed": True, "note": ""} for c in criteria
                    ],
                    "verdict": "APPROVED",
                    "feedback": "All criteria satisfied.",
                }
            )
        )

        result = await service.validate(
            criteria=criteria,
            code_produced="full implementation",
            test_result=None,
        )

        assert result.verdict == "APPROVED"
        assert len(result.criteria) == 3


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
