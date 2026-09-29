from pathlib import Path

from anthropic import AsyncAnthropic

from tessera.services.providers.agent_sdk import ClaudeAgentSDKProvider
from tessera.services.providers.anthropic_api import AnthropicApiProvider
from tessera.services.providers.base import (
    LLMProvider,
    ProviderResult,
    StreamCallback,
    ToolEventCallback,
)

__all__ = [
    "AnthropicApiProvider",
    "ClaudeAgentSDKProvider",
    "LLMProvider",
    "ProviderResult",
    "StreamCallback",
    "ToolEventCallback",
    "get_provider",
]


def get_provider(
    name: str | None = None,
    api_key: str = "",
    *,
    max_turns: int | None = None,
    max_budget_usd: float | None = None,
    allow_tools: bool = True,
    tools: list[str] | None = None,
    racine_ecriture: Path | None = None,
    skills: list[str] | None = None,
) -> LLMProvider:
    """Builds the configured LLM provider. Defaults to the subscription-backed SDK.

    ``max_turns``/``max_budget_usd`` are the quota guardrails threaded down to
    ``ClaudeAgentSDKProvider`` (ignored by ``anthropic_api``, which has no
    turn loop or subscription budget to bound). Leaving them ``None`` falls
    back to ``ClaudeAgentSDKProvider``'s own defaults.

    ``allow_tools=False`` produces a provider with no file/shell tools
    *available* — not merely un-approved — for pure text-in/JSON-out
    services (validator, security auditor, planner, project analyzer, agent
    creator, project creator, doc updater) that have no use for them. Both
    the SDK's ``tools`` (availability) and ``allowed_tools`` (auto-approval)
    fields are set to the same empty list, since ``allowed_tools`` alone
    cannot disable the CLI's default toolset (ticket-044 merge-gate review,
    finding 1). Ignored by ``anthropic_api``, which never grants tools.

    ``tools`` names an explicit subset, for callers that need *some* tools but
    not all of them — the chat of ticket-048 takes the file tools and no shell
    one. It wins over ``allow_tools``, which is all-or-nothing.

    ``racine_ecriture`` is the write root a pipeline run froze before its
    first agent (ticket-119); only the SDK provider has a perimeter hook to
    hand it to.

    ``skills`` names the skills the role may load (ticket-242); only the SDK
    provider has a `Skill` tool to give.
    """
    resolved = name or "agent_sdk"
    if resolved == "agent_sdk":
        kwargs: dict[str, object] = {}
        if racine_ecriture is not None:
            kwargs["racine_ecriture"] = racine_ecriture
        if max_turns is not None:
            kwargs["max_turns"] = max_turns
        if max_budget_usd is not None:
            kwargs["max_budget_usd"] = max_budget_usd
        if skills:
            kwargs["skills"] = list(skills)
        if tools is not None:
            kwargs["allowed_tools"] = list(tools)
        elif not allow_tools:
            kwargs["allowed_tools"] = []
        return ClaudeAgentSDKProvider(**kwargs)  # type: ignore[arg-type]
    if resolved == "anthropic_api":
        if not api_key:
            raise ValueError(
                "Le provider 'anthropic_api' exige une ANTHROPIC_API_KEY. "
                "Renseignez-la dans .env, ou laissez llm_provider='agent_sdk' "
                "pour utiliser votre abonnement."
            )
        return AnthropicApiProvider(AsyncAnthropic(api_key=api_key))
    if resolved == "ollama":
        # Sans outils quoi qu'on demande : il sert les rôles texte→JSON, et
        # la boucle agentique reste au SDK (ticket-189).
        from tessera.config import settings
        from tessera.services.providers.ollama import OllamaProvider

        return OllamaProvider(settings.ollama_base_url)
    raise ValueError(
        f"Provider LLM inconnu : {resolved!r}. "
        "Valeurs acceptées : 'agent_sdk', 'anthropic_api', 'ollama'."
    )
