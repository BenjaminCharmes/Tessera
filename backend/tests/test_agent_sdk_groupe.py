"""The agent's CLI lives in a process group closed with the call (ticket-900)."""
import asyncio
import logging
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from claude_agent_sdk import ClaudeAgentOptions, ResultMessage

from tessera.services.providers import agent_sdk as agent_sdk_module
from tessera.services.providers.agent_sdk import ClaudeAgentSDKProvider
from tessera.services.providers.noms import ProviderIndisponible

PID_DU_CLI = 4242
GROUPE = object()


class Traces:
    """What the doubles of the group functions were asked."""

    def __init__(self) -> None:
        self.rattaches: list[int] = []
        self.fermes: list[object] = []


def _resultat() -> ResultMessage:
    return ResultMessage(
        subtype="success", duration_ms=1, duration_api_ms=1, is_error=False,
        num_turns=1, session_id="s", total_cost_usd=0.0, usage=None, result="ok",
    )


@pytest.fixture
def traces(monkeypatch: pytest.MonkeyPatch) -> Traces:
    t = Traces()

    def rattacher(groupe: object, pid: int) -> bool:
        t.rattaches.append(pid)
        return True

    monkeypatch.setattr(agent_sdk_module, "creer_groupe", lambda: GROUPE)
    monkeypatch.setattr(agent_sdk_module, "rattacher_au_groupe", rattacher)
    monkeypatch.setattr(agent_sdk_module, "fermer_le_groupe", lambda g: t.fermes.append(g) or True)
    return t


def _faux_query(*, bloque: bool = False) -> Any:
    async def fake_query(
        *, prompt: str, options: ClaudeAgentOptions, transport: Any
    ) -> AsyncIterator[Any]:
        transport._au_demarrage(PID_DU_CLI)
        if bloque:
            await asyncio.sleep(60)
        yield _resultat()

    return fake_query


async def _appel(provider: ClaudeAgentSDKProvider) -> Any:
    return await provider.complete(
        system="s", user="u", model="m", max_tokens=10, cwd=Path.cwd()
    )


async def test_normal_flow_attaches_the_cli_pid_and_closes_the_group(
    monkeypatch: pytest.MonkeyPatch, traces: Traces
) -> None:
    monkeypatch.setattr(agent_sdk_module, "query", _faux_query())
    await _appel(ClaudeAgentSDKProvider())
    assert traces.rattaches == [PID_DU_CLI]
    assert traces.fermes == [GROUPE]


async def test_silence_closes_the_group(
    monkeypatch: pytest.MonkeyPatch, traces: Traces
) -> None:
    monkeypatch.setattr(agent_sdk_module, "query", _faux_query(bloque=True))
    with pytest.raises(ProviderIndisponible):
        await _appel(ClaudeAgentSDKProvider(silence_max_s=0.05))
    assert traces.fermes == [GROUPE]


async def test_cancellation_closes_the_group(
    monkeypatch: pytest.MonkeyPatch, traces: Traces
) -> None:
    monkeypatch.setattr(agent_sdk_module, "query", _faux_query(bloque=True))
    tache = asyncio.create_task(_appel(ClaudeAgentSDKProvider(silence_max_s=0)))
    await asyncio.sleep(0.05)
    tache.cancel()
    with pytest.raises(asyncio.CancelledError):
        await tache
    assert traces.fermes == [GROUPE]


async def test_without_a_group_the_call_runs_and_logs_it(
    monkeypatch: pytest.MonkeyPatch, traces: Traces, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(agent_sdk_module, "creer_groupe", lambda: None)
    monkeypatch.setattr(agent_sdk_module, "query", _faux_query())
    with caplog.at_level(logging.WARNING):
        await _appel(ClaudeAgentSDKProvider())
    assert "agent_sans_groupe" in caplog.text
    assert traces.rattaches == []
