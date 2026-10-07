"""Tests for SecurityAuditorService (ticket-037)."""

import json
from pathlib import Path

import pytest

from tests.test_providers_base import FakeProvider
from tessera.services.security_auditor import (
    SecurityAuditResult,
    SecurityAuditorService,
    SecurityIssue,
)


@pytest.fixture
def provider() -> FakeProvider:
    return FakeProvider()


@pytest.fixture
def service(provider: FakeProvider) -> SecurityAuditorService:
    return SecurityAuditorService(provider, Path("agents/prompts"))


def _set_response(provider: FakeProvider, data: dict) -> None:
    provider.set_content(json.dumps(data))


class TestSecurityAuditorService:
    async def test_pass_verdict_on_clean_code(
        self, service: SecurityAuditorService, provider: FakeProvider, tmp_path: Path
    ) -> None:
        _set_response(
            provider, {"issues": [], "verdict": "PASS", "summary": "No issues."}
        )

        result = await service.audit("def safe(): return 42", tmp_path)

        assert result.verdict == "PASS"
        assert result.issues == []
        assert result.has_critical is False
        assert result.has_high is False

    async def test_block_verdict_on_critical_issue(
        self, service: SecurityAuditorService, provider: FakeProvider, tmp_path: Path
    ) -> None:
        _set_response(
            provider,
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
            },
        )

        result = await service.audit("query = f'SELECT * FROM users WHERE id={id}'", tmp_path)

        assert result.verdict == "BLOCK"
        assert result.has_critical is True
        assert len(result.issues) == 1
        assert result.issues[0].severity == "CRITICAL"

    async def test_block_verdict_on_high_severity(
        self, service: SecurityAuditorService, provider: FakeProvider, tmp_path: Path
    ) -> None:
        _set_response(
            provider,
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
            },
        )

        result = await service.audit("API_KEY = 'sk-abc123'", tmp_path)

        assert result.verdict == "BLOCK"
        assert result.has_high is True

    async def test_pass_verdict_on_medium_only(
        self, service: SecurityAuditorService, provider: FakeProvider, tmp_path: Path
    ) -> None:
        _set_response(
            provider,
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
            },
        )

        result = await service.audit("@app.route('/api')", tmp_path)

        assert result.verdict == "PASS"
        assert result.has_critical is False
        assert result.has_high is False
        assert len(result.issues) == 1

    async def test_bloque_sur_json_illisible(
        self, service: SecurityAuditorService, provider: FakeProvider, tmp_path: Path
    ) -> None:
        # Un JSON illisible valait PASS : l'audit échouait ouvert, et un diff
        # dangereux passait parce que l'auditeur avait mal répondu (ticket-122).
        _set_response(provider, {})

        result = await service.audit("code", tmp_path)

        assert result.verdict == "BLOCK"
        assert result.reason
        assert result.reason in result.summary

    async def test_bloque_quand_le_provider_est_indisponible(
        self, service: SecurityAuditorService, tmp_path: Path
    ) -> None:
        # Provider en panne valait PASS par défaut. Un audit qui n'a pas eu
        # lieu ne peut pas approuver ; le `reason` doit dire pourquoi à l'écran.
        class _FailingProvider(FakeProvider):
            async def complete(self, **kwargs):  # type: ignore[override]
                raise Exception("Network error")

        service_with_failure = SecurityAuditorService(_FailingProvider(), Path("agents/prompts"))

        result = await service_with_failure.audit("code", tmp_path)

        assert result.verdict == "BLOCK"
        assert "Network error" in result.reason
        assert result.reason in result.summary

    async def test_un_issue_high_bloque_malgre_un_verdict_pass(
        self, service: SecurityAuditorService, provider: FakeProvider, tmp_path: Path
    ) -> None:
        # `has_high` était calculé mais ne gatait rien : le LLM pouvait lister
        # une faille HIGH et conclure PASS, et le pipeline suivait le PASS.
        _set_response(
            provider,
            {
                "verdict": "PASS",
                "summary": "ok",
                "issues": [
                    {"severity": "HIGH", "type": "xss", "location": "a.py:1",
                     "description": "d", "fix": "f"}
                ],
            },
        )

        result = await service.audit("code", tmp_path)

        assert result.verdict == "BLOCK"
        assert "HIGH" in result.reason

    async def test_audit_result_properties(
        self, service: SecurityAuditorService, provider: FakeProvider, tmp_path: Path
    ) -> None:
        _set_response(
            provider,
            {
                "issues": [
                    {"severity": "CRITICAL", "type": "x", "location": "y", "description": "z", "fix": ""},
                    {"severity": "LOW", "type": "a", "location": "b", "description": "c", "fix": ""},
                ],
                "verdict": "BLOCK",
                "summary": "Critical found.",
            },
        )

        result = await service.audit("code", tmp_path)

        assert result.has_critical is True
        assert result.has_high is False
        assert len(result.issues) == 2

    async def test_calls_provider_with_expected_shape(
        self, service: SecurityAuditorService, provider: FakeProvider, tmp_path: Path
    ) -> None:
        _set_response(provider, {"issues": [], "verdict": "PASS", "summary": "ok"})

        await service.audit("some code diff", tmp_path)

        assert len(provider.calls) == 1
        call = provider.calls[0]
        assert call["mode"] == "complete"
        assert "some code diff" in call["user"]
        assert isinstance(call["system"], str)
        assert call["max_tokens"] > 0


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


class TestAuditWithLeadingJsonObject:
    """Tests for ticket-371 — audit skips JSON objects that lack the verdict key."""

    async def test_block_when_leading_json_precedes_block_verdict(
        self, service: SecurityAuditorService, provider: FakeProvider, tmp_path: Path
    ) -> None:
        # ticket-371 : un objet JSON sans "verdict" cité avant le verdict réel
        # était pris comme réponse et valait PASS par défaut (ADR-039).
        verdict_obj = {"issues": [], "verdict": "BLOCK", "summary": "Injection found."}
        provider.set_content(
            '{"project_id": "abc"}\n\nSome analysis.\n\n'
            + __import__("json").dumps(verdict_obj)
        )

        result = await service.audit("unsafe code", tmp_path)

        assert result.verdict == "BLOCK"

    async def test_block_when_no_object_has_verdict_key(
        self, service: SecurityAuditorService, provider: FakeProvider, tmp_path: Path
    ) -> None:
        # ticket-371 : une réponse sans aucun objet portant "verdict" doit
        # bloquer (ADR-039 : l'audit échoue fermé), jamais rendre PASS.
        provider.set_content(
            '{"project_id": "abc"} {"issues": [], "summary": "no verdict key"}'
        )

        result = await service.audit("some code", tmp_path)

        assert result.verdict == "BLOCK"
        assert result.reason


async def test_a_whole_branch_diff_reaches_the_auditor_intact(
    service: SecurityAuditorService, provider: FakeProvider, tmp_path: Path
) -> None:
    # ticket-221 : depuis le ticket-208, l'audit reçoit tout le diff d'une
    # branche reprise. Coupé à 16 000 caractères, du code passait sans audit.
    _set_response(provider, {"issues": [], "verdict": "PASS", "summary": "ok"})
    diff = "+x = 1\n" * 10_000 + "+SENTINELLE_FIN_DU_DIFF\n"

    await service.audit(diff, tmp_path)

    assert "SENTINELLE_FIN_DU_DIFF" in provider.calls[0]["user"]
