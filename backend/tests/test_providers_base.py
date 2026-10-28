import json
from pathlib import Path
from typing import Any

import pytest

from tessera.services.providers.base import (
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
        self._structured: dict[str, Any] | None = None
        self._structured_forced = False

    def set_content(self, content: str) -> None:
        """Changes the canned response without reaching into `_content` directly."""
        self._content = content

    def set_structured(self, data: dict[str, Any] | None) -> None:
        """Forces the structured output returned when a schema is passed (None = absent)."""
        self._structured = data
        self._structured_forced = True

    def _structured_for(self, schema: dict[str, Any] | None) -> dict[str, Any] | None:
        """What a provider with a valid structured output would return for ``schema``.

        Without a schema: None, as the real providers do. With one: the forced
        value, else the canned text when it is a JSON object, else None.
        """
        if schema is None:
            return None
        if self._structured_forced:
            return self._structured
        try:
            data = json.loads(self._content)
        except ValueError:
            return None
        return data if isinstance(data, dict) else None

    async def complete(
        self,
        *,
        system: str,
        user: str,
        model: str,
        max_tokens: int,
        cwd: Path | None = None,
        **extra: Any,
    ) -> ProviderResult:
        # `extra` capture ce que le runner ne transmet que lorsqu'il a quelque
        # chose à transmettre — `session` (ticket-187), `ask_user`. Un test
        # peut ainsi vérifier qu'un paramètre est absent, pas seulement nul.
        self.calls.append(
            {"mode": "complete", "system": system, "user": user,
             "model": model, "max_tokens": max_tokens, "cwd": cwd, **extra}
        )
        return ProviderResult(
            content=self._content,
            input_tokens=self._tokens,
            output_tokens=self._tokens,
            cost_usd=self._cost_usd,
            provider_name=self.name,
            structured=self._structured_for(extra.get("schema")),
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
        **extra: Any,
    ) -> ProviderResult:
        self.calls.append(
            {"mode": "stream", "system": system, "user": user,
             "model": model, "max_tokens": max_tokens, "cwd": cwd,
             "on_token": on_token, "on_tool_use": on_tool_use, **extra}
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
