import pytest

from tessera.services.providers import get_provider
from tessera.services.providers.agent_sdk import ClaudeAgentSDKProvider
from tessera.services.providers.anthropic_api import AnthropicApiProvider


def test_get_provider_agent_sdk() -> None:
    assert isinstance(get_provider("agent_sdk"), ClaudeAgentSDKProvider)


def test_get_provider_anthropic_api() -> None:
    provider = get_provider("anthropic_api", api_key="sk-test")
    assert isinstance(provider, AnthropicApiProvider)


def test_get_provider_api_sans_cle_est_une_erreur_explicite() -> None:
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        get_provider("anthropic_api", api_key="")


def test_get_provider_inconnu_est_une_erreur_explicite() -> None:
    with pytest.raises(ValueError, match="inconnu"):
        get_provider("gpt5")


def test_get_provider_thread_max_turns_et_max_budget_usd() -> None:
    """Regression — ticket-044 review, finding 1: production hardcoded
    max_turns=30 / max_budget_usd=None because get_provider never forwarded
    them. The budget cap is the guardrail that actually bounds spend."""
    provider = get_provider("agent_sdk", max_turns=7, max_budget_usd=3.5)
    assert isinstance(provider, ClaudeAgentSDKProvider)
    assert provider._max_turns == 7
    assert provider._max_budget_usd == 3.5


def test_get_provider_sans_garde_fous_utilise_les_defauts_du_provider() -> None:
    provider = get_provider("agent_sdk")
    assert isinstance(provider, ClaudeAgentSDKProvider)
    assert provider._max_turns == 30
    assert provider._max_budget_usd is None


def test_get_provider_allow_tools_false_produit_un_provider_sans_outils() -> None:
    """Regression — ticket-044 review, finding 4: pure text-in/JSON-out
    services (validator, security_auditor, planner, project_analyzer,
    agent_creator) have no use for file/shell tools."""
    provider = get_provider("agent_sdk", allow_tools=False)
    assert isinstance(provider, ClaudeAgentSDKProvider)
    assert provider._allowed_tools == []


async def test_get_provider_allow_tools_false_desactive_reellement_les_outils(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression — ticket-044 merge-gate finding 1 (critical): pinning only
    ``_allowed_tools`` cannot distinguish "tools unavailable" from "tools
    available but not auto-approved" — an empty ``allowed_tools`` list makes
    the SDK CLI omit ``--allowedTools`` entirely, leaving the full built-in
    toolset available. This asserts the ``tools`` field actually reaching the
    SDK options is ``[]``, not merely ``allowed_tools``."""
    from collections.abc import AsyncIterator
    from typing import Any

    import tessera.services.providers.agent_sdk as agent_sdk_module
    from claude_agent_sdk import ResultMessage

    captured: dict[str, object] = {}

    async def fake_query(*, prompt: str, options: Any) -> AsyncIterator[Any]:
        captured["tools"] = options.tools
        captured["allowed_tools"] = options.allowed_tools
        yield ResultMessage(
            subtype="success", duration_ms=1, duration_api_ms=1,
            is_error=False, num_turns=1, session_id="sess-1",
            total_cost_usd=None, usage=None,
        )

    monkeypatch.setattr(agent_sdk_module, "query", fake_query)

    provider = get_provider("agent_sdk", allow_tools=False)
    await provider.complete(system="sys", user="user", model="claude-sonnet-4-6", max_tokens=100)  # type: ignore[union-attr]

    assert captured["allowed_tools"] == []
    assert captured["tools"] == []


def test_get_provider_allow_tools_true_par_defaut() -> None:
    provider = get_provider("agent_sdk")
    assert isinstance(provider, ClaudeAgentSDKProvider)
    assert provider._allowed_tools == ClaudeAgentSDKProvider.ALLOWED_TOOLS


def test_get_provider_allow_tools_false_est_sans_effet_sur_anthropic_api() -> None:
    """anthropic_api never grants tools, so allow_tools is simply ignored —
    it must not raise or otherwise change the provider it returns."""
    provider = get_provider("anthropic_api", api_key="sk-test", allow_tools=False)
    assert isinstance(provider, AnthropicApiProvider)


def test_get_provider_accepte_un_jeu_d_outils_explicite() -> None:
    # Le chat (ticket-048) n'expose aucun outil shell : `allow_tools` est
    # tout-ou-rien, il faut pouvoir demander un sous-ensemble précis.
    provider = get_provider(tools=["Read", "Write", "Edit", "Glob", "Grep"])

    assert provider._allowed_tools == ["Read", "Write", "Edit", "Glob", "Grep"]
    assert "Bash" not in provider._allowed_tools
