"""A Bash call with no result is cut at its own bound (ticket-957)."""
import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ResultMessage, ToolResultBlock, ToolUseBlock, UserMessage

from tessera.services.providers import agent_sdk as agent_sdk_module
from tessera.services.providers.agent_sdk import ClaudeAgentSDKProvider
from tessera.services.providers.noms import ProviderIndisponible


def _usage(outil: str) -> AssistantMessage:
    return AssistantMessage(content=[ToolUseBlock(id="t1", name=outil, input={})], model="m")


def _retour() -> UserMessage:
    return UserMessage(content=[ToolResultBlock(tool_use_id="t1", content="ok")])


def _resultat() -> ResultMessage:
    return ResultMessage(
        subtype="success", duration_ms=1, duration_api_ms=1, is_error=False,
        num_turns=1, session_id="s", total_cost_usd=0.0, usage=None, result="ok",
    )


def _flux(*messages: Any, pause: float = 0.0) -> Any:
    async def fake_query(
        *, prompt: str, options: ClaudeAgentOptions, transport: Any
    ) -> AsyncIterator[Any]:
        for m in messages:
            yield m
        await asyncio.sleep(pause)
        yield _resultat()

    return fake_query


async def _appel(provider: ClaudeAgentSDKProvider) -> Any:
    return await provider.complete(system="s", user="u", model="m", max_tokens=10, cwd=Path.cwd())


async def test_bash_without_result_is_cut_at_the_bash_bound(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agent_sdk_module, "query", _flux(_usage("Bash"), pause=5))
    with pytest.raises(ProviderIndisponible, match="appel Bash"):
        await _appel(ClaudeAgentSDKProvider(silence_max_s=30, bash_silence_max_s=0.05))


async def test_bound_is_general_again_after_the_tool_result(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agent_sdk_module, "query", _flux(_usage("Bash"), _retour(), pause=5))
    with pytest.raises(ProviderIndisponible, match="agent silencieux"):
        await _appel(ClaudeAgentSDKProvider(silence_max_s=0.05, bash_silence_max_s=0.01))


async def test_another_tool_keeps_the_general_bound(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agent_sdk_module, "query", _flux(_usage("Read"), pause=0.15))
    result = await _appel(ClaudeAgentSDKProvider(silence_max_s=1, bash_silence_max_s=0.05))
    assert result is not None


async def test_zero_disables_the_bash_bound(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agent_sdk_module, "query", _flux(_usage("Bash"), pause=0.15))
    result = await _appel(ClaudeAgentSDKProvider(silence_max_s=1, bash_silence_max_s=0))
    assert result is not None
