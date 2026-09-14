from pathlib import Path

from anthropic import AsyncAnthropic
from anthropic.types import TextBlockParam

from vibe_ide.services.providers.base import (
    ProviderResult,
    StreamCallback,
    ToolEventCallback,
)


def _system_blocks(system: str) -> list[TextBlockParam]:
    """Builds the system blocks for a Messages API call.

    An empty (or whitespace-only) system string produces no block at all —
    the Messages API rejects an empty text block with a 400, so callers that
    pass ``system=""`` (e.g. the bootstrap-agent prompt in
    ``ProjectCreatorService``) must not trip that failure.
    """
    if not system.strip():
        return []
    return [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]


class AnthropicApiProvider:
    """Messages API backend. Billed against prepaid API credits, no file tools."""

    name = "anthropic_api"

    def __init__(self, client: AsyncAnthropic) -> None:
        self._client = client

    async def complete(
        self,
        *,
        system: str,
        user: str,
        model: str,
        max_tokens: int,
        cwd: Path | None = None,
    ) -> ProviderResult:
        response = await self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=_system_blocks(system),
            messages=[{"role": "user", "content": user}],
        )
        content = "".join(b.text for b in response.content if hasattr(b, "text"))
        return _result_from(content, response.usage)

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
        chunks: list[str] = []
        async with self._client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=_system_blocks(system),
            messages=[{"role": "user", "content": user}],
        ) as stream:
            async for text in stream.text_stream:
                chunks.append(text)
                if on_token is not None:
                    await on_token(text)
            message = await stream.get_final_message()
        return _result_from("".join(chunks), message.usage)


def _result_from(content: str, usage: object) -> ProviderResult:
    """Construct a ProviderResult from response content and usage stats."""
    return ProviderResult(
        content=content,
        input_tokens=getattr(usage, "input_tokens", 0) or 0,
        output_tokens=getattr(usage, "output_tokens", 0) or 0,
        cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
        cache_creation_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
        provider_name=AnthropicApiProvider.name,
    )
