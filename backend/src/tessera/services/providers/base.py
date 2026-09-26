from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

StreamCallback = Callable[[str], Awaitable[None]]
ToolEventCallback = Callable[[str, dict[str, Any]], Awaitable[None]]


@dataclass
class ProviderResult:
    """Normalized outcome of a single LLM call, whatever the backing provider."""

    content: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    # Renseigné par les providers qui rapportent eux-mêmes leur coût (SDK).
    # Laissé à None par ceux dont le coût se calcule à partir des tokens.
    cost_usd: float | None = None
    provider_name: str = ""
    # L'identifiant de la conversation, pour la reprendre au tour suivant
    # (ticket-187). Seul le SDK en rend un ; un provider muet laisse None, et
    # le tour suivant repart alors à froid, comme avant.
    session_id: str | None = None
    # Le modèle qui a réellement répondu, quand ce n'est pas celui demandé —
    # un repli (ticket-188). Vide sinon : l'appelant garde le sien.
    model: str = ""


@runtime_checkable
class LLMProvider(Protocol):
    """Contract every LLM backend must satisfy to be used by AgentRunner."""

    name: str

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
    ) -> ProviderResult:
        """Runs a single call and returns the full response.

        ``ask_user`` is only honoured by providers that can expose tools. It is
        passed only when a dialogue channel is attached to the run, so a
        provider that ignores it simply never lets an agent ask (ticket-066).

        ``session`` resumes a previous conversation of this provider, identified
        by the ``session_id`` of an earlier result (ticket-187). Like
        ``ask_user`` it is only passed when there is one, so providers and test
        doubles that cannot resume never see it. A provider that cannot resume
        a given session falls back to a fresh call rather than failing.

        ``max_tokens`` is best-effort: it is honoured only by providers whose
        backend exposes an actual output-length cap. ``AnthropicApiProvider``
        forwards it straight to the Messages API and it is enforced.
        ``ClaudeAgentSDKProvider`` accepts it to satisfy this protocol but
        ``ClaudeAgentOptions`` has no equivalent field, so it is silently
        discarded — callers relying on it to bound output length get no such
        guarantee under the default (``agent_sdk``) provider.
        """
        ...

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
    ) -> ProviderResult:
        """Runs a single call, forwarding incremental output to the callbacks.

        See :meth:`complete` for the ``max_tokens`` best-effort caveat — it
        applies identically here.
        """
        ...
