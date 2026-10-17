"""Tests for the auditor reading the project before it blocks (ticket-485)."""

from pathlib import Path
from typing import Any

import pytest

from tests.test_providers_base import FakeProvider
from tessera.services.security_auditor import SecurityAuditorService

_PROMPTS = Path(__file__).resolve().parents[2] / "agents" / "prompts"


class _ToolFailingProvider(FakeProvider):
    """Raises the way the SDK does when a tool read fails mid-audit."""

    async def complete(self, **kwargs: Any) -> Any:  # type: ignore[override]
        raise RuntimeError("Read tool unavailable")


async def test_audit_runs_inside_the_project(tmp_path: Path) -> None:
    provider = FakeProvider(content='{"issues": [], "verdict": "PASS", "summary": "ok"}')
    service = SecurityAuditorService(provider, _PROMPTS)

    await service.audit("+x = 1", tmp_path)

    assert provider.calls[0]["cwd"] == tmp_path.resolve()


async def test_tool_error_during_audit_blocks_with_a_reason(tmp_path: Path) -> None:
    service = SecurityAuditorService(_ToolFailingProvider(), _PROMPTS)

    result = await service.audit("+x = 1", tmp_path)

    assert result.verdict == "BLOCK"
    assert "Read tool unavailable" in result.reason


async def test_unreadable_answer_after_reading_still_blocks(tmp_path: Path) -> None:
    provider = FakeProvider(content="je n'ai pas fini de lire")
    service = SecurityAuditorService(provider, _PROMPTS)

    result = await service.audit("+x = 1", tmp_path)

    assert result.verdict == "BLOCK"
    assert result.reason


_PASS = '{"issues": [], "verdict": "PASS", "summary": "ok"}'
_TURN_LIMIT = "Reached maximum number of turns (20)"


class _FailingProvider(FakeProvider):
    """Fails every call with the given error."""

    def __init__(self, message: str) -> None:
        super().__init__()
        self._message = message

    async def complete(self, **kwargs: Any) -> Any:  # type: ignore[override]
        self.calls.append(kwargs)
        raise RuntimeError(self._message)


async def test_prompt_budget_comes_from_the_setting(tmp_path: Path) -> None:
    provider = FakeProvider(content=_PASS)
    service = SecurityAuditorService(provider, _PROMPTS, max_turns=42)

    await service.audit("+x = 1", tmp_path)

    system = provider.calls[0]["system"]
    assert "au plus 42 lectures" in system
    assert "garde le dernier tour pour ton verdict" in system
    assert "summary" in system


async def test_turn_limit_retries_once_on_the_diff_alone(tmp_path: Path) -> None:
    tools = _FailingProvider(_TURN_LIMIT)
    diff_only = FakeProvider(content=_PASS)
    service = SecurityAuditorService(
        tools, _PROMPTS, max_turns=20, diff_only_provider=diff_only
    )

    result = await service.audit("+x = 1", tmp_path)

    assert result.verdict == "PASS"
    assert len(tools.calls) == 1
    assert len(diff_only.calls) == 1
    assert "au plus 20 lectures" in tools.calls[0]["system"]
    assert "au plus" not in diff_only.calls[0]["system"]
    assert "maximum number of turns" in result.fallback_reason


async def test_two_failures_in_a_row_block(tmp_path: Path) -> None:
    service = SecurityAuditorService(
        _FailingProvider(_TURN_LIMIT), _PROMPTS,
        diff_only_provider=_FailingProvider("provider down"),
    )

    result = await service.audit("+x = 1", tmp_path)

    assert result.verdict == "BLOCK"
    assert "provider down" in result.reason
    assert result.fallback_reason


async def test_another_error_does_not_fall_back(tmp_path: Path) -> None:
    diff_only = FakeProvider(content=_PASS)
    service = SecurityAuditorService(
        _FailingProvider("Read tool unavailable"), _PROMPTS, diff_only_provider=diff_only
    )

    result = await service.audit("+x = 1", tmp_path)

    assert result.verdict == "BLOCK"
    assert diff_only.calls == []
    assert result.fallback_reason == ""


async def test_turn_limit_without_a_fallback_provider_blocks(tmp_path: Path) -> None:
    service = SecurityAuditorService(_FailingProvider(_TURN_LIMIT), _PROMPTS)

    result = await service.audit("+x = 1", tmp_path)

    assert result.verdict == "BLOCK"
    assert "maximum number of turns" in result.reason


@pytest.fixture
def prompt() -> str:
    # Espaces normalisés : un retour à la ligne dans le prompt ne casse rien.
    return " ".join((_PROMPTS / "securite.md").read_text(encoding="utf-8").split())


def test_prompt_tells_the_auditor_which_tools_it_has(prompt: str) -> None:
    assert all(tool in prompt for tool in ("Read", "Glob", "Grep"))


def test_prompt_asks_to_read_code_outside_the_diff_before_a_block(prompt: str) -> None:
    assert "absent du diff" in prompt
    assert "lis ce code" in prompt
    assert "BLOCK" in prompt


def test_prompt_asks_to_cite_the_guard_or_its_absence(prompt: str) -> None:
    assert "ligne de garde" in prompt
    assert "garde est absente" in prompt


def test_prompt_states_the_real_truncation_limit(prompt: str) -> None:
    assert "16 000" not in prompt
    assert "120 000" in prompt
