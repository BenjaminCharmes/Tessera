from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    HookMatcher,
    RateLimitEvent,
    ResultMessage,
    StreamEvent,
    TextBlock,
    ToolUseBlock,
    query,
)

from vibe_ide.services.providers.git_guard import hook_refus_git
from vibe_ide.services.providers.ask_user import (
    ASK_USER_SERVER_NAME,
    ASK_USER_TOOL_NAME,
    build_ask_user_server,
)
from vibe_ide.services.providers.base import (
    ProviderResult,
    StreamCallback,
    ToolEventCallback,
)
from vibe_ide.services.quota_tracker import QuotaTracker

_ALLOWED_TOOLS = ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]


def _build_options(
    *,
    system: str,
    model: str,
    max_turns: int,
    max_budget_usd: float | None,
    cwd: Path | None,
    allowed_tools: list[str] | None = None,
    ask_user: Callable[[str], Awaitable[str]] | None = None,
) -> ClaudeAgentOptions:
    """Builds SDK options with the guardrails established by the ticket-044 spike."""
    # ``allowed_tools`` only controls auto-approval — the SDK CLI's
    # subprocess transport reads ``if effective_allowed_tools:`` and omits
    # ``--allowedTools`` entirely when the list is empty, leaving the CLI's
    # full default toolset available. Only ``tools`` controls which built-in
    # tools exist at all (``[]`` disables all of them). Both fields are
    # always set to the same resolved list here, so a "no tools" request
    # (`allowed_tools=[]`) actually disables tool availability instead of
    # merely withholding auto-approval, and no configuration path can end up
    # with an implicit toolset (ticket-044 merge-gate review, finding 1).
    effective_tools = allowed_tools if allowed_tools is not None else _ALLOWED_TOOLS

    # L'outil `ask_user` n'existe que si un canal de dialogue est branché sur
    # ce run (ticket-066). Le donner sans canal reviendrait à promettre à
    # l'agent une réponse que personne ne pourrait lui apporter.
    mcp_servers: dict[str, Any] = {}
    if ask_user is not None:
        mcp_servers[ASK_USER_SERVER_NAME] = build_ask_user_server(ask_user)
        effective_tools = [*effective_tools, ASK_USER_TOOL_NAME]

    # Une ANTHROPIC_API_KEY présente dans l'environnement est PRIORITAIRE sur
    # la session Claude Code dans le CLI. En mode abonnement — le défaut — elle
    # ne sert donc à rien et casse tout : le CLI tente de s'authentifier avec
    # elle et remonte `401 API key is invalid`. Le placeholder `sk-ant-...`
    # livré dans `.env.example` suffit à faire échouer *tous* les appels
    # agent, avec un message d'erreur qui ne pointe jamais vers `.env`.
    # On la neutralise explicitement pour le sous-process du SDK ; la clef
    # reste disponible pour `AnthropicApiProvider`, qui est le seul à devoir
    # l'utiliser.
    env = {"ANTHROPIC_API_KEY": ""}

    return ClaudeAgentOptions(
        env=env,
        # Chemin long obligatoire : un chemin court Windows 8.3 fait refuser
        # les écritures.
        cwd=str(cwd.resolve()) if cwd is not None else None,
        system_prompt=system,
        model=model,
        # permission_mode seul ne suffit pas — allowed_tools doit être explicite.
        permission_mode="acceptEdits",
        tools=effective_tools,
        allowed_tools=effective_tools,
        setting_sources=["project"],
        include_partial_messages=True,
        max_turns=max_turns,
        max_budget_usd=max_budget_usd,
        mcp_servers=mcp_servers,
        # Les agents n'écrivent pas dans l'historique git : le pipeline crée la
        # branche et commite lui-même (ADR-018), et ne merge jamais (ADR-022).
        # Le refus est posé ici, en `PreToolUse`, parce qu'une entrée de
        # `allowed_tools` couvrant `Bash` l'auto-approuverait avant tout
        # callback de permission — le garde serait inerte (ticket-068).
        hooks={"PreToolUse": [HookMatcher(matcher="Bash", hooks=[hook_refus_git])]},
    )


def _extract_stream_delta(event: dict[str, Any]) -> str | None:
    """Extracts incremental text from a raw Anthropic ``stream_event`` payload.

    ``StreamEvent.event`` is the raw Anthropic Messages API streaming event
    (``message_start``, ``content_block_start``, ``content_block_delta``,
    ``content_block_stop``, ``message_delta``, ``message_stop``, ...). Only a
    ``content_block_delta`` carrying a ``text_delta`` produces visible text
    for live display; every other shape — including a malformed/unexpected
    one — yields ``None`` rather than raising, since a live-token feed must
    never crash the run.
    """
    try:
        if event.get("type") != "content_block_delta":
            return None
        delta = event.get("delta") or {}
        if delta.get("type") != "text_delta":
            return None
        text = delta.get("text")
        return text if isinstance(text, str) and text else None
    except AttributeError:
        return None


def _usage_from(result: Any) -> tuple[int, int, int, int]:
    """Extracts (input, output, cache_read, cache_creation) from a ResultMessage."""
    usage = getattr(result, "usage", None) or {}
    return (
        int(usage.get("input_tokens", 0) or 0),
        int(usage.get("output_tokens", 0) or 0),
        int(usage.get("cache_read_input_tokens", 0) or 0),
        int(usage.get("cache_creation_input_tokens", 0) or 0),
    )


class ClaudeAgentSDKProvider:
    """Claude Agent SDK backend: real file tools, billed against the subscription."""

    name = "agent_sdk"
    ALLOWED_TOOLS = _ALLOWED_TOOLS

    def __init__(
        self,
        max_turns: int = 30,
        max_budget_usd: float | None = None,
        allowed_tools: list[str] | None = None,
    ) -> None:
        self._max_turns = max_turns
        self._max_budget_usd = max_budget_usd
        # Le provider est le seul endroit qui voit les messages du SDK : c'est
        # donc ici que le quota se capte, et sa forme s'arrête ici (ticket-054).
        self.quota = QuotaTracker()
        self._allowed_tools = list(allowed_tools) if allowed_tools is not None else list(_ALLOWED_TOOLS)

    async def complete(
        self,
        *,
        system: str,
        user: str,
        model: str,
        max_tokens: int,
        cwd: Path | None = None,
        ask_user: Callable[[str], Awaitable[str]] | None = None,
    ) -> ProviderResult:
        # NB : max_tokens est reçu pour satisfaire le protocole LLMProvider mais
        # ClaudeAgentOptions n'expose aucun champ équivalent — il est ignoré ici.
        # Voir LLMProvider.complete pour la portée exacte de cette limitation.
        return await self._run(
            system=system, user=user, model=model, cwd=cwd, ask_user=ask_user
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
        ask_user: Callable[[str], Awaitable[str]] | None = None,
    ) -> ProviderResult:
        # NB : max_tokens est ignoré — voir la note dans complete() ci-dessus.
        return await self._run(
            system=system, user=user, model=model, cwd=cwd,
            on_token=on_token, on_tool_use=on_tool_use, ask_user=ask_user,
        )

    async def _run(
        self,
        *,
        system: str,
        user: str,
        model: str,
        cwd: Path | None,
        on_token: StreamCallback | None = None,
        on_tool_use: ToolEventCallback | None = None,
        ask_user: Callable[[str], Awaitable[str]] | None = None,
    ) -> ProviderResult:
        options = _build_options(
            system=system, model=model, max_turns=self._max_turns,
            max_budget_usd=self._max_budget_usd, cwd=cwd,
            allowed_tools=self._allowed_tools, ask_user=ask_user,
        )
        chunks: list[str] = []
        result: ResultMessage | None = None

        async for message in query(prompt=user, options=options):
            if isinstance(message, RateLimitEvent):
                # L'état du quota d'abonnement : la seule mesure de la
                # ressource réellement finie en mode abonnement. Un provider
                # qui n'en émet pas laisse le tracker vide, et rien ne casse.
                self.quota.observe(getattr(message, "rate_limit_info", None))
            elif isinstance(message, ResultMessage):
                result = message
            elif isinstance(message, StreamEvent):
                # Forwarded live for display only — the authoritative record
                # of content is the buffered TextBlock below, so this must
                # never also be appended to `chunks` (would double the text).
                if on_token is not None:
                    delta = _extract_stream_delta(message.event)
                    if delta:
                        await on_token(delta)
            elif isinstance(message, AssistantMessage):
                for block in message.content:
                    # isinstance plutôt que comparaison de type().__name__ :
                    # robuste et vérifiable statiquement (finding 2, revue ticket-044).
                    if isinstance(block, TextBlock):
                        chunks.append(block.text)
                    elif isinstance(block, ToolUseBlock) and on_tool_use is not None:
                        await on_tool_use(block.name, dict(block.input))

        if result is None:
            raise RuntimeError("Agent SDK: aucun ResultMessage reçu")

        inp, out, cache_read, cache_creation = _usage_from(result)
        return ProviderResult(
            content="".join(chunks),
            input_tokens=inp,
            output_tokens=out,
            cache_read_tokens=cache_read,
            cache_creation_tokens=cache_creation,
            cost_usd=result.total_cost_usd,
            provider_name=self.name,
        )
