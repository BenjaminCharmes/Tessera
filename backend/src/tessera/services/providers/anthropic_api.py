from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from anthropic import AsyncAnthropic
from anthropic.types import TextBlockParam

from tessera.services.providers.base import (
    ProviderResult,
    StreamCallback,
    ToolEventCallback,
)


#: Le nom de l'outil unique par lequel la Messages API rend une sortie
#: structurée : son `input_schema` est le schéma, et `tool_choice` le force.
OUTIL_SORTIE = "structured_output"


def _kwargs_schema(schema: dict[str, Any] | None) -> dict[str, Any]:
    """The ``tools``/``tool_choice`` kwargs forcing ``schema``; empty without one.

    Rien n'est ajouté sans schéma : l'appel garde exactement sa forme d'avant.
    """
    if schema is None:
        return {}
    return {
        "tools": [
            {
                "name": OUTIL_SORTIE,
                "description": "Rend la réponse sous la forme demandée.",
                "input_schema": schema,
            }
        ],
        "tool_choice": {"type": "tool", "name": OUTIL_SORTIE},
    }


def _structured_from(content: list[Any]) -> dict[str, Any] | None:
    """The ``input`` of the forced ``tool_use`` block, or ``None`` when absent."""
    for bloc in content:
        if getattr(bloc, "type", None) == "tool_use" and getattr(bloc, "name", None) == OUTIL_SORTIE:
            entree = getattr(bloc, "input", None)
            return entree if isinstance(entree, dict) else None
    return None


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
        ask_user: Callable[[str], Awaitable[str]] | None = None,
        session: str | None = None,
        schema: dict[str, Any] | None = None,
    ) -> ProviderResult:
        # `session` est ignoré : la Messages API n'a pas de conversation à
        # reprendre, chaque appel est complet (ticket-187).
        response = await self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=_system_blocks(system),
            messages=[{"role": "user", "content": user}],
            **_kwargs_schema(schema),
        )
        content = "".join(b.text for b in response.content if hasattr(b, "text"))
        result = _result_from(content, response.usage)
        if schema is not None:
            result.structured = _structured_from(response.content)
        return result

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
        ask_user: Callable[[str], Awaitable[str]] | None = None,
        session: str | None = None,
        schema: dict[str, Any] | None = None,
    ) -> ProviderResult:
        chunks: list[str] = []
        async with self._client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=_system_blocks(system),
            messages=[{"role": "user", "content": user}],
            **_kwargs_schema(schema),
        ) as stream:
            async for text in stream.text_stream:
                chunks.append(text)
                if on_token is not None:
                    await on_token(text)
            message = await stream.get_final_message()
        result = _result_from("".join(chunks), message.usage)
        if schema is not None:
            result.structured = _structured_from(message.content)
        return result


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
