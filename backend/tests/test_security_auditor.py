"""Tests for SecurityAuditorService (ticket-037)."""

import json
from pathlib import Path

import pytest

from tests.test_providers_base import FakeProvider
from tessera.services.security_auditor import (
    _SEVERITIES,
    SecurityAuditResult,
    SecurityAuditorService,
    SecurityIssue,
)
from tessera.services.security_schema import SECURITY_SCHEMA


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


class TestIntroducedField:
    """Tests for ticket-387 — only introduced issues trigger BLOCK."""

    async def test_high_preexisting_does_not_block(
        self, service: SecurityAuditorService, provider: FakeProvider, tmp_path: Path
    ) -> None:
        # Un HIGH dans le contexte (code déjà mergé) ne doit pas bloquer le
        # ticket courant : introduced: false signale un problème préexistant.
        _set_response(
            provider,
            {
                "verdict": "PASS",
                "summary": "Context-only flaw, not introduced here.",
                "issues": [
                    {
                        "severity": "HIGH",
                        "type": "localStorage secret",
                        "location": "auth.ts:12",
                        "description": "Token stored in localStorage",
                        "fix": "Use httpOnly cookie",
                        "introduced": False,
                    }
                ],
            },
        )

        result = await service.audit("+ localStorage.clear()", tmp_path)

        assert result.verdict == "PASS"

    async def test_high_introduced_blocks_even_when_verdict_is_pass(
        self, service: SecurityAuditorService, provider: FakeProvider, tmp_path: Path
    ) -> None:
        # Un HIGH introduced: true impose BLOCK même si l'auditeur a conclu PASS.
        _set_response(
            provider,
            {
                "verdict": "PASS",
                "summary": "ok",
                "issues": [
                    {
                        "severity": "HIGH",
                        "type": "XSS",
                        "location": "a.tsx:5",
                        "description": "Unescaped HTML",
                        "fix": "Escape output",
                        "introduced": True,
                    }
                ],
            },
        )

        result = await service.audit("+ dangerouslySetInnerHTML", tmp_path)

        assert result.verdict == "BLOCK"
        assert "HIGH" in result.reason

    async def test_high_without_introduced_field_defaults_to_block(
        self, service: SecurityAuditorService, provider: FakeProvider, tmp_path: Path
    ) -> None:
        # Champ absent → True par défaut (échec fermé, ADR-039).
        _set_response(
            provider,
            {
                "verdict": "PASS",
                "summary": "ok",
                "issues": [
                    {
                        "severity": "HIGH",
                        "type": "SQL Injection",
                        "location": "db.py:10",
                        "description": "Unsafe query",
                        "fix": "Use parameterized queries",
                        # pas de champ "introduced"
                    }
                ],
            },
        )

        result = await service.audit("+ query = f'SELECT * FROM {id}'", tmp_path)

        assert result.verdict == "BLOCK"

    @pytest.mark.parametrize("valeur", [None, 0, "", "false"])
    async def test_high_with_non_boolean_introduced_still_blocks(
        self,
        service: SecurityAuditorService,
        provider: FakeProvider,
        tmp_path: Path,
        valeur: object,
    ) -> None:
        # Seul un False explicite exempte : null, 0, "" ou "false" bloquent.
        _set_response(
            provider,
            {
                "verdict": "PASS",
                "summary": "ok",
                "issues": [
                    {
                        "severity": "HIGH",
                        "type": "SQL Injection",
                        "location": "db.py:10",
                        "description": "Unsafe query",
                        "fix": "Use parameterized queries",
                        "introduced": valeur,
                    }
                ],
            },
        )

        result = await service.audit("+ query = f'SELECT * FROM {id}'", tmp_path)

        assert result.verdict == "BLOCK"

    async def test_preexisting_issue_included_in_result(
        self, service: SecurityAuditorService, provider: FakeProvider, tmp_path: Path
    ) -> None:
        # Un problème préexistant doit figurer dans issues pour être transmis
        # au reviewer, même s'il ne bloque pas.
        _set_response(
            provider,
            {
                "verdict": "PASS",
                "summary": "Preexisting flaw noted.",
                "issues": [
                    {
                        "severity": "HIGH",
                        "type": "localStorage secret",
                        "location": "auth.ts:12",
                        "description": "Token in localStorage",
                        "fix": "Use httpOnly cookie",
                        "introduced": False,
                    }
                ],
            },
        )

        result = await service.audit("+ localStorage.clear()", tmp_path)

        assert result.verdict == "PASS"
        assert len(result.issues) == 1
        assert result.issues[0].introduced is False
        assert result.issues[0].severity == "HIGH"


class TestStructuredOutput:
    """Tests for ticket-613 — the verdict is read from the structured output (ADR-061)."""

    async def test_schema_is_passed_to_the_provider(
        self, service: SecurityAuditorService, provider: FakeProvider, tmp_path: Path
    ) -> None:
        _set_response(provider, {"issues": [], "verdict": "PASS", "summary": "ok"})

        await service.audit("code", tmp_path)

        assert provider.calls[0]["schema"] == SECURITY_SCHEMA

    async def test_verdict_comes_from_structured_not_from_text(
        self, service: SecurityAuditorService, provider: FakeProvider, tmp_path: Path
    ) -> None:
        # Le texte dit PASS, la sortie structurée dit BLOCK : seule la seconde compte.
        provider.set_content('{"issues": [], "verdict": "PASS", "summary": "texte"}')
        provider.set_structured({"issues": [], "verdict": "BLOCK", "summary": "structuré"})

        result = await service.audit("code", tmp_path)

        assert result.verdict == "BLOCK"
        assert result.summary == "structuré"

    async def test_absent_structured_blocks_after_the_retry(
        self, service: SecurityAuditorService, provider: FakeProvider, tmp_path: Path
    ) -> None:
        # Un texte JSON lisible ne suffit plus : sans sortie structurée, BLOCK.
        provider.set_content('{"issues": [], "verdict": "PASS", "summary": "ok"}')
        provider.set_structured(None)

        result = await service.audit("code", tmp_path)

        assert result.verdict == "BLOCK"
        assert "deux tentatives" in result.reason
        assert len(provider.calls) == 2

    async def test_structured_without_verdict_blocks(
        self, service: SecurityAuditorService, provider: FakeProvider, tmp_path: Path
    ) -> None:
        # ADR-039 : un objet qui contredit le schéma ne rend jamais PASS.
        provider.set_structured({"issues": [], "summary": "no verdict key"})

        result = await service.audit("some code", tmp_path)

        assert result.verdict == "BLOCK"
        assert result.reason

    async def test_any_verdict_other_than_pass_blocks(
        self, service: SecurityAuditorService, provider: FakeProvider, tmp_path: Path
    ) -> None:
        provider.set_structured({"issues": [], "verdict": "pass", "summary": "ok"})

        result = await service.audit("code", tmp_path)

        assert result.verdict == "BLOCK"

    async def test_summary_with_a_windows_path_is_kept_as_is(
        self, service: SecurityAuditorService, provider: FakeProvider, tmp_path: Path
    ) -> None:
        # Plus de JSON à réparer : un antislash du résumé passe tel quel.
        provider.set_structured(
            {"issues": [], "verdict": "PASS", "summary": "Path ..\\x is safe."}
        )

        result = await service.audit("code", tmp_path)

        assert result.verdict == "PASS"
        assert result.summary == "Path ..\\x is safe."

    @pytest.mark.parametrize("severity", ["CRITICAL", "HIGH"])
    async def test_critical_or_high_blocks_despite_a_structured_pass(
        self,
        service: SecurityAuditorService,
        provider: FakeProvider,
        tmp_path: Path,
        severity: str,
    ) -> None:
        provider.set_structured(
            {
                "verdict": "PASS",
                "summary": "ok",
                "issues": [
                    {"severity": severity, "description": "d", "introduced": True}
                ],
            }
        )

        result = await service.audit("code", tmp_path)

        assert result.verdict == "BLOCK"
        assert severity in result.reason

    def test_severity_enum_matches_the_service_severities(self) -> None:
        enum = SECURITY_SCHEMA["properties"]["issues"]["items"]["properties"]["severity"]["enum"]
        assert set(enum) == set(_SEVERITIES)

    def test_required_keys_match_the_contract(self) -> None:
        item = SECURITY_SCHEMA["properties"]["issues"]["items"]
        assert set(SECURITY_SCHEMA["required"]) == {"verdict", "issues", "summary"}
        assert set(item["required"]) == {"severity", "description", "introduced"}
        assert SECURITY_SCHEMA["properties"]["verdict"]["enum"] == ["PASS", "BLOCK"]


_PROMPT = Path(__file__).resolve().parents[2] / "agents" / "prompts" / "securite.md"


def test_security_prompt_names_the_schema_fields() -> None:
    prompt = _PROMPT.read_text(encoding="utf-8")
    item = SECURITY_SCHEMA["properties"]["issues"]["items"]["properties"]
    fields = set(SECURITY_SCHEMA["properties"]) | set(item)
    for field in fields:
        assert f"`{field}`" in prompt, field
    assert "```json" not in prompt


_PASS_JSON = json.dumps({"issues": [], "verdict": "PASS", "summary": "ok"})


class _SequencedProvider(FakeProvider):
    """Answers with each queued reply in turn; an Exception item is raised."""

    def __init__(self, replies: list[str | Exception]) -> None:
        super().__init__()
        self._replies = replies

    async def complete(self, **kwargs):  # type: ignore[override]
        reply = self._replies[len(self.calls)]
        if isinstance(reply, Exception):
            self.calls.append({"mode": "complete", **kwargs})
            raise reply
        self.set_content(reply)
        return await super().complete(**kwargs)


class TestUnreadableAnswerRetried:
    """Tests for ticket-436 — an unreadable answer is asked again once."""

    async def test_unreadable_then_pass_gives_pass_in_two_calls(self, tmp_path: Path) -> None:
        provider = _SequencedProvider(["not json at all", _PASS_JSON])
        service = SecurityAuditorService(provider, Path("agents/prompts"))

        result = await service.audit("code", tmp_path)

        assert result.verdict == "PASS"
        assert result.reason == ""
        assert len(provider.calls) == 2

    async def test_second_attempt_carries_the_reminder(self, tmp_path: Path) -> None:
        provider = _SequencedProvider(["nope", _PASS_JSON])
        service = SecurityAuditorService(provider, Path("agents/prompts"))

        await service.audit("code", tmp_path)

        users = [c["user"] for c in provider.calls]
        assert "n'était pas un JSON valide" not in users[0]
        assert "n'était pas un JSON valide" in users[-1]

    async def test_two_unreadable_answers_block_and_say_so(self, tmp_path: Path) -> None:
        provider = _SequencedProvider(["nope", "still nope"])
        service = SecurityAuditorService(provider, Path("agents/prompts"))

        result = await service.audit("code", tmp_path)

        assert result.verdict == "BLOCK"
        assert "deux tentatives" in result.reason
        assert result.reason in result.summary

    async def test_provider_exception_blocks_without_second_attempt(
        self, tmp_path: Path
    ) -> None:
        provider = _SequencedProvider([Exception("Network error")])
        service = SecurityAuditorService(provider, Path("agents/prompts"))

        result = await service.audit("code", tmp_path)

        assert result.verdict == "BLOCK"
        assert "Network error" in result.reason
        assert len(provider.calls) == 1

    async def test_readable_first_answer_costs_a_single_call(
        self, service: SecurityAuditorService, provider: FakeProvider, tmp_path: Path
    ) -> None:
        provider.set_content(_PASS_JSON)

        await service.audit("code", tmp_path)

        assert len(provider.calls) == 1


async def test_a_whole_branch_diff_reaches_the_auditor_intact(
    service: SecurityAuditorService, provider: FakeProvider, tmp_path: Path
) -> None:
    # ticket-221 : depuis le ticket-208, l'audit reçoit tout le diff d'une
    # branche reprise. Coupé à 16 000 caractères, du code passait sans audit.
    _set_response(provider, {"issues": [], "verdict": "PASS", "summary": "ok"})
    diff = "+x = 1\n" * 10_000 + "+SENTINELLE_FIN_DU_DIFF\n"

    await service.audit(diff, tmp_path)

    assert "SENTINELLE_FIN_DU_DIFF" in provider.calls[0]["user"]
