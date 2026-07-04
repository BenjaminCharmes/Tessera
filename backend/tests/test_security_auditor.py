"""Tests for SecurityAuditorService (ticket-037)."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from vibe_ide.services.security_auditor import (
    SecurityAuditResult,
    SecurityAuditorService,
    SecurityIssue,
)


@pytest.fixture
def service() -> SecurityAuditorService:
    mock_client = MagicMock()
    return SecurityAuditorService(mock_client, Path("agents/prompts"))


def _make_llm_response(data: dict) -> MagicMock:
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=json.dumps(data))]
    return mock_msg


class TestSecurityAuditorService:
    async def test_pass_verdict_on_clean_code(
        self, service: SecurityAuditorService, tmp_path: Path
    ) -> None:
        service._client.messages.create = AsyncMock(
            return_value=_make_llm_response(
                {"issues": [], "verdict": "PASS", "summary": "No issues."}
            )
        )

        result = await service.audit("def safe(): return 42", tmp_path)

        assert result.verdict == "PASS"
        assert result.issues == []
        assert result.has_critical is False
        assert result.has_high is False

    async def test_block_verdict_on_critical_issue(
        self, service: SecurityAuditorService, tmp_path: Path
    ) -> None:
        service._client.messages.create = AsyncMock(
            return_value=_make_llm_response(
                {
                    "issues": [
                        {
                            "severity": "CRITICAL",
                            "type": "SQL Injection",
                            "location": "db.py:10",
                            "description": "Unsafe query",
                            "fix": "Use parameterized queries",
                        }
                    ],
                    "verdict": "BLOCK",
                    "summary": "SQL injection found.",
                }
            )
        )

        result = await service.audit("query = f'SELECT * FROM users WHERE id={id}'", tmp_path)

        assert result.verdict == "BLOCK"
        assert result.has_critical is True
        assert len(result.issues) == 1
        assert result.issues[0].severity == "CRITICAL"

    async def test_block_verdict_on_high_severity(
        self, service: SecurityAuditorService, tmp_path: Path
    ) -> None:
        service._client.messages.create = AsyncMock(
            return_value=_make_llm_response(
                {
                    "issues": [
                        {
                            "severity": "HIGH",
                            "type": "Hardcoded Secret",
                            "location": "config.py:3",
                            "description": "API key in source",
                            "fix": "Use environment variable",
                        }
                    ],
                    "verdict": "BLOCK",
                    "summary": "Hardcoded secret found.",
                }
            )
        )

        result = await service.audit("API_KEY = 'sk-abc123'", tmp_path)

        assert result.verdict == "BLOCK"
        assert result.has_high is True

    async def test_pass_verdict_on_medium_only(
        self, service: SecurityAuditorService, tmp_path: Path
    ) -> None:
        service._client.messages.create = AsyncMock(
            return_value=_make_llm_response(
                {
                    "issues": [
                        {
                            "severity": "MEDIUM",
                            "type": "Missing rate limit",
                            "location": "api.py:20",
                            "description": "No rate limiting",
                            "fix": "Add rate limiting middleware",
                        }
                    ],
                    "verdict": "PASS",
                    "summary": "Medium issues only.",
                }
            )
        )

        result = await service.audit("@app.route('/api')", tmp_path)

        assert result.verdict == "PASS"
        assert result.has_critical is False
        assert result.has_high is False
        assert len(result.issues) == 1

    async def test_pass_on_invalid_json_response(
        self, service: SecurityAuditorService, tmp_path: Path
    ) -> None:
        service._client.messages.create = AsyncMock(
            return_value=_make_llm_response({})
        )

        result = await service.audit("code", tmp_path)

        assert result.verdict == "PASS"

    async def test_pass_on_llm_failure(
        self, service: SecurityAuditorService, tmp_path: Path
    ) -> None:
        service._client.messages.create = AsyncMock(side_effect=Exception("Network error"))

        result = await service.audit("code", tmp_path)

        assert result.verdict == "PASS"

    async def test_audit_result_properties(
        self, service: SecurityAuditorService, tmp_path: Path
    ) -> None:
        service._client.messages.create = AsyncMock(
            return_value=_make_llm_response(
                {
                    "issues": [
                        {"severity": "CRITICAL", "type": "x", "location": "y", "description": "z", "fix": ""},
                        {"severity": "LOW", "type": "a", "location": "b", "description": "c", "fix": ""},
                    ],
                    "verdict": "BLOCK",
                    "summary": "Critical found.",
                }
            )
        )

        result = await service.audit("code", tmp_path)

        assert result.has_critical is True
        assert result.has_high is False
        assert len(result.issues) == 2


class TestSecurityIssue:
    def test_dataclass(self) -> None:
        issue = SecurityIssue(
            severity="HIGH",
            type="SQL Injection",
            location="db.py:10",
            description="Unsafe",
            fix="Parameterize",
        )
        assert issue.severity == "HIGH"


class TestSecurityAuditResult:
    def test_has_critical_computed(self) -> None:
        result = SecurityAuditResult(
            issues=[SecurityIssue("CRITICAL", "x", "y", "z", "")],
            verdict="BLOCK",
            summary="x",
        )
        assert result.has_critical is True
        assert result.has_high is False

    def test_has_high_computed(self) -> None:
        result = SecurityAuditResult(
            issues=[SecurityIssue("HIGH", "x", "y", "z", "")],
            verdict="BLOCK",
            summary="x",
        )
        assert result.has_high is True
        assert result.has_critical is False
