from pathlib import Path
from typing import Any

import pytest

from vibe_ide.services.providers.base import (
    LLMProvider,
    ProviderResult,
    StreamCallback,
    ToolEventCallback,
)


class FakeProvider:
    """Test double implementing LLMProvider. Records the calls it receives."""

    name = "fake"

    def __init__(
        self,
        content: str = "réponse",
        tokens: int = 10,
        cost_usd: float | None = None,
    ) -> None:
        self._content = content
        self._tokens = tokens
        self._cost_usd = cost_usd
        self.calls: list[dict[str, Any]] = []

    def set_content(self, content: str) -> None:
        """Changes the canned response without reaching into `_content` directly."""
        self._content = content

    async def complete(
        self,
        *,
        system: str,
        user: str,
        model: str,
        max_tokens: int,
        cwd: Path | None = None,
    ) -> ProviderResult:
        self.calls.append(
            {"mode": "complete", "system": system, "user": user,
             "model": model, "max_tokens": max_tokens, "cwd": cwd}
        )
        return ProviderResult(
            content=self._content,
            input_tokens=self._tokens,
            output_tokens=self._tokens,
            cost_usd=self._cost_usd,
            provider_name=self.name,
        )

    async def stream(
        self,
        *,
        system: str,
        user: str,
        model: str,
        max_tokens: int,
        cwd: Path | None = None,
        on_token: StreamCallback | None = None,
        on_tool_use: ToolEventCallback | None = None,
    ) -> ProviderResult:
        self.calls.append(
            {"mode": "stream", "system": system, "user": user,
             "model": model, "max_tokens": max_tokens, "cwd": cwd,
             "on_token": on_token, "on_tool_use": on_tool_use}
        )
        if on_token is not None:
            for chunk in self._content.split(" "):
                await on_token(chunk + " ")
        return ProviderResult(
            content=self._content,
            input_tokens=self._tokens,
            output_tokens=self._tokens,
            cost_usd=self._cost_usd,
            provider_name=self.name,
        )


def test_provider_result_defauts() -> None:
    result = ProviderResult(content="abc")
    assert result.content == "abc"
    assert result.input_tokens == 0
    assert result.output_tokens == 0
    assert result.cache_read_tokens == 0
    assert result.cache_creation_tokens == 0
    assert result.cost_usd is None
    assert result.provider_name == ""


def test_fake_provider_satisfait_le_protocole() -> None:
    provider: LLMProvider = FakeProvider()
    assert isinstance(provider, LLMProvider)


@pytest.mark.asyncio
async def test_complete_renvoie_un_provider_result() -> None:
    provider = FakeProvider(content="bonjour")
    result = await provider.complete(
        system="sys", user="usr", model="claude-sonnet-4-6", max_tokens=100
    )
    assert result.content == "bonjour"
    assert result.provider_name == "fake"


@pytest.mark.asyncio
async def test_stream_appelle_on_token() -> None:
    provider = FakeProvider(content="un deux trois")
    recus: list[str] = []

    async def on_token(chunk: str) -> None:
        recus.append(chunk)

    result = await provider.stream(
        system="sys", user="usr", model="claude-sonnet-4-6",
        max_tokens=100, on_token=on_token,
    )
    assert "".join(recus).strip() == "un deux trois"
    assert result.content == "un deux trois"


@pytest.mark.asyncio
async def test_stream_enregistre_les_callbacks_dans_calls() -> None:
    provider = FakeProvider(content="x")

    async def on_token(chunk: str) -> None:
        pass

    async def on_tool_use(name: str, payload: dict[str, Any]) -> None:
        pass

    await provider.stream(
        system="sys", user="usr", model="claude-sonnet-4-6", max_tokens=100,
        on_token=on_token, on_tool_use=on_tool_use,
    )
    assert provider.calls[0]["on_token"] is on_token
    assert provider.calls[0]["on_tool_use"] is on_tool_use


def test_set_content_change_la_reponse_canned() -> None:
    provider = FakeProvider(content="initial")
    provider.set_content("nouvelle reponse")
    assert provider._content == "nouvelle reponse"
