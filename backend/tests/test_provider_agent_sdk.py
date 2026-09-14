from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
)

import vibe_ide.services.providers.agent_sdk as agent_sdk_module
from claude_agent_sdk import StreamEvent
from vibe_ide.services.providers.agent_sdk import (
    ClaudeAgentSDKProvider,
    _build_options,
    _extract_stream_delta,
    _usage_from,
)


def test_nom_du_provider() -> None:
    assert ClaudeAgentSDKProvider().name == "agent_sdk"


def test_allowed_tools_est_explicite() -> None:
    # permission_mode seul ne suffit pas : sans allowed_tools les écritures
    # sont refusées (constat du spike ticket-044).
    assert ClaudeAgentSDKProvider.ALLOWED_TOOLS == [
        "Read", "Write", "Edit", "Bash", "Glob", "Grep"
    ]


def test_build_options_resout_le_cwd_en_chemin_long(tmp_path: Path) -> None:
    projet = tmp_path / "projet"
    projet.mkdir()
    options = _build_options(
        system="sys", model="claude-sonnet-4-6", max_turns=30,
        max_budget_usd=None, cwd=projet,
    )
    assert options.cwd == str(projet.resolve())


def test_build_options_sans_cwd(tmp_path: Path) -> None:
    options = _build_options(
        system="sys", model="claude-sonnet-4-6", max_turns=30,
        max_budget_usd=None, cwd=None,
    )
    assert options.cwd is None


def test_build_options_porte_les_garde_fous() -> None:
    options = _build_options(
        system="mon prompt", model="claude-sonnet-4-6", max_turns=12,
        max_budget_usd=1.5, cwd=None,
    )
    assert options.system_prompt == "mon prompt"
    assert options.model == "claude-sonnet-4-6"
    assert options.max_turns == 12
    assert options.max_budget_usd == 1.5
    assert options.permission_mode == "acceptEdits"
    assert options.allowed_tools == ClaudeAgentSDKProvider.ALLOWED_TOOLS
    assert options.setting_sources == ["project"]
    assert options.include_partial_messages is True


def test_build_options_jeu_d_outils_complet_explicite_les_deux_champs() -> None:
    """Regression — ticket-044 merge-gate finding 1: ``tools`` must be set
    explicitly alongside ``allowed_tools`` on every path, full-toolset
    included, so no configuration can end up with an implicit toolset."""
    options = _build_options(
        system="mon prompt", model="claude-sonnet-4-6", max_turns=12,
        max_budget_usd=1.5, cwd=None,
    )
    assert options.tools == ClaudeAgentSDKProvider.ALLOWED_TOOLS


def test_build_options_avec_allowed_tools_personnalise() -> None:
    options = _build_options(
        system="sys", model="claude-sonnet-4-6", max_turns=30,
        max_budget_usd=None, cwd=None, allowed_tools=[],
    )
    assert options.allowed_tools == []


def test_build_options_tools_vide_desactive_reellement_les_outils() -> None:
    """Regression — ticket-044 merge-gate finding 1 (critical): the SDK CLI
    only reads ``--allowedTools`` (auto-approval) when
    ``effective_allowed_tools`` is truthy — an empty list is falsy and the
    flag is omitted, leaving the CLI's full default toolset available. Only
    the ``tools`` field actually disables built-in tools (``[]`` = none
    available). ``allowed_tools=[]`` must therefore also set ``tools=[]``."""
    options = _build_options(
        system="sys", model="claude-sonnet-4-6", max_turns=30,
        max_budget_usd=None, cwd=None, allowed_tools=[],
    )
    assert options.tools == []


def test_provider_allowed_tools_par_defaut_est_la_liste_complete() -> None:
    provider = ClaudeAgentSDKProvider()
    assert provider._allowed_tools == ClaudeAgentSDKProvider.ALLOWED_TOOLS


def test_provider_allowed_tools_personnalise() -> None:
    provider = ClaudeAgentSDKProvider(allowed_tools=[])
    assert provider._allowed_tools == []


async def test_run_transmet_allowed_tools_personnalise_aux_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_options: dict[str, Any] = {}

    async def fake_query(*, prompt: str, options: Any) -> AsyncIterator[Any]:
        captured_options["allowed_tools"] = options.allowed_tools
        yield _make_result_message(usage=None, total_cost_usd=None)

    monkeypatch.setattr(agent_sdk_module, "query", fake_query)

    provider = ClaudeAgentSDKProvider(allowed_tools=[])
    await provider.complete(system="sys", user="user", model="claude-sonnet-4-6", max_tokens=100)

    assert captured_options["allowed_tools"] == []


def test_usage_from_extrait_les_quatre_compteurs() -> None:
    result = MagicMock()
    result.usage = {
        "input_tokens": 10,
        "output_tokens": 801,
        "cache_read_input_tokens": 109258,
        "cache_creation_input_tokens": 10313,
    }
    assert _usage_from(result) == (10, 801, 109258, 10313)


def test_usage_from_tolere_un_usage_absent() -> None:
    result = MagicMock()
    result.usage = None
    assert _usage_from(result) == (0, 0, 0, 0)


def test_usage_from_tolere_des_champs_manquants() -> None:
    result = MagicMock()
    result.usage = {"input_tokens": 5}
    assert _usage_from(result) == (5, 0, 0, 0)


def _make_result_message(
    *,
    usage: dict[str, Any] | None,
    total_cost_usd: float | None,
) -> ResultMessage:
    return ResultMessage(
        subtype="success",
        duration_ms=1,
        duration_api_ms=1,
        is_error=False,
        num_turns=1,
        session_id="sess-1",
        total_cost_usd=total_cost_usd,
        usage=usage,
    )


def _patch_query(monkeypatch: pytest.MonkeyPatch, messages: list[Any]) -> None:
    """Replaces claude_agent_sdk.query (as imported in agent_sdk) with a
    fake async generator, so the test runs without a network call."""

    async def fake_query(*, prompt: str, options: Any) -> AsyncIterator[Any]:
        for message in messages:
            yield message

    monkeypatch.setattr(agent_sdk_module, "query", fake_query)


async def test_complete_retourne_un_provider_result_correct(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assistant = AssistantMessage(
        content=[TextBlock(text="bon"), TextBlock(text="jour")],
        model="claude-sonnet-4-6",
    )
    result = _make_result_message(
        usage={
            "input_tokens": 10,
            "output_tokens": 20,
            "cache_read_input_tokens": 30,
            "cache_creation_input_tokens": 40,
        },
        total_cost_usd=0.42,
    )
    _patch_query(monkeypatch, [assistant, result])

    provider = ClaudeAgentSDKProvider()
    outcome = await provider.complete(
        system="sys", user="user", model="claude-sonnet-4-6", max_tokens=100
    )

    assert outcome.content == "bonjour"
    assert outcome.input_tokens == 10
    assert outcome.output_tokens == 20
    assert outcome.cache_read_tokens == 30
    assert outcome.cache_creation_tokens == 40
    assert outcome.cost_usd == 0.42
    assert outcome.provider_name == "agent_sdk"


async def test_complete_ne_declenche_aucun_callback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # complete() n'a pas de paramètres on_token/on_tool_use : on vérifie que
    # _run ne plante pas et n'appelle rien de tel en leur absence.
    assistant = AssistantMessage(
        content=[
            TextBlock(text="salut"),
            ToolUseBlock(id="t1", name="Read", input={"path": "a.py"}),
        ],
        model="claude-sonnet-4-6",
    )
    result = _make_result_message(usage=None, total_cost_usd=None)
    _patch_query(monkeypatch, [assistant, result])

    provider = ClaudeAgentSDKProvider()
    outcome = await provider.complete(
        system="sys", user="user", model="claude-sonnet-4-6", max_tokens=100
    )
    assert outcome.content == "salut"


async def test_complete_resout_le_cwd(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    projet = tmp_path / "projet"
    projet.mkdir()
    captured_options: dict[str, Any] = {}

    async def fake_query(*, prompt: str, options: Any) -> AsyncIterator[Any]:
        captured_options["cwd"] = options.cwd
        yield _make_result_message(usage=None, total_cost_usd=None)

    monkeypatch.setattr(agent_sdk_module, "query", fake_query)

    provider = ClaudeAgentSDKProvider()
    await provider.complete(
        system="sys", user="user", model="claude-sonnet-4-6",
        max_tokens=100, cwd=projet,
    )

    assert captured_options["cwd"] == str(projet.resolve())


def _stream_event(text_delta: str) -> StreamEvent:
    """Builds a StreamEvent carrying a raw Anthropic content_block_delta/text_delta."""
    return StreamEvent(
        uuid="evt-1",
        session_id="sess-1",
        event={"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": text_delta}},
    )


async def test_stream_appelle_on_token_incrementalement_via_stream_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Finding 3, ticket-044 review: on_token must fire per StreamEvent delta,
    not once per completed TextBlock — else the UI degrades from a live
    stream to a few large end-of-turn bursts."""
    events = [_stream_event("un"), _stream_event("deux"), _stream_event("trois")]
    assistant = AssistantMessage(
        content=[TextBlock(text="undeuxtrois")], model="claude-sonnet-4-6"
    )
    result = _make_result_message(usage=None, total_cost_usd=None)
    _patch_query(monkeypatch, [*events, assistant, result])

    recus: list[str] = []

    async def on_token(text: str) -> None:
        recus.append(text)

    provider = ClaudeAgentSDKProvider()
    outcome = await provider.stream(
        system="sys", user="user", model="claude-sonnet-4-6",
        max_tokens=100, on_token=on_token,
    )

    assert recus == ["un", "deux", "trois"]
    # The buffered TextBlock is the authoritative content — forwarding both
    # it and the deltas to `content` would duplicate the text.
    assert outcome.content == "undeuxtrois"


async def test_stream_evenement_de_forme_inattendue_ne_plante_pas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A StreamEvent whose raw `event` dict doesn't match the expected
    content_block_delta/text_delta shape must be silently ignored, not
    crash the run."""
    weird_events = [
        StreamEvent(uuid="e1", session_id="s1", event={"type": "message_start"}),
        StreamEvent(uuid="e2", session_id="s1", event={"type": "content_block_delta", "delta": {"type": "input_json_delta", "partial_json": "{}"}}),
        StreamEvent(uuid="e3", session_id="s1", event={}),
    ]
    assistant = AssistantMessage(content=[TextBlock(text="ok")], model="claude-sonnet-4-6")
    result = _make_result_message(usage=None, total_cost_usd=None)
    _patch_query(monkeypatch, [*weird_events, assistant, result])

    recus: list[str] = []

    async def on_token(text: str) -> None:
        recus.append(text)

    provider = ClaudeAgentSDKProvider()
    outcome = await provider.stream(
        system="sys", user="user", model="claude-sonnet-4-6",
        max_tokens=100, on_token=on_token,
    )

    assert recus == []
    assert outcome.content == "ok"


def test_extract_stream_delta_extrait_le_texte() -> None:
    event = {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "salut"}}
    assert _extract_stream_delta(event) == "salut"


def test_extract_stream_delta_ignore_les_autres_types_de_delta() -> None:
    event = {"type": "content_block_delta", "delta": {"type": "input_json_delta", "partial_json": "{}"}}
    assert _extract_stream_delta(event) is None


def test_extract_stream_delta_ignore_les_autres_types_d_evenement() -> None:
    assert _extract_stream_delta({"type": "message_stop"}) is None


def test_extract_stream_delta_tolere_un_dict_vide() -> None:
    assert _extract_stream_delta({}) is None


async def test_stream_appelle_on_tool_use_pour_chaque_bloc_outil(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assistant = AssistantMessage(
        content=[
            ToolUseBlock(id="t1", name="Read", input={"path": "a.py"}),
            TextBlock(text="ignore-moi"),
            ToolUseBlock(id="t2", name="Bash", input={"command": "ls"}),
        ],
        model="claude-sonnet-4-6",
    )
    result = _make_result_message(usage=None, total_cost_usd=None)
    _patch_query(monkeypatch, [assistant, result])

    appels: list[tuple[str, dict[str, Any]]] = []

    async def on_tool_use(name: str, tool_input: dict[str, Any]) -> None:
        appels.append((name, tool_input))

    provider = ClaudeAgentSDKProvider()
    await provider.stream(
        system="sys", user="user", model="claude-sonnet-4-6",
        max_tokens=100, on_tool_use=on_tool_use,
    )

    assert appels == [
        ("Read", {"path": "a.py"}),
        ("Bash", {"command": "ls"}),
    ]


async def test_stream_ignore_les_blocs_non_text_non_tool_use(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assistant = AssistantMessage(
        content=[
            ThinkingBlock(thinking="je reflechis", signature="sig"),
            ToolResultBlock(tool_use_id="t1", content="ok"),
            TextBlock(text="reponse"),
        ],
        model="claude-sonnet-4-6",
    )
    result = _make_result_message(usage=None, total_cost_usd=None)
    _patch_query(monkeypatch, [_stream_event("reponse"), assistant, result])

    recus: list[str] = []

    async def on_token(text: str) -> None:
        recus.append(text)

    provider = ClaudeAgentSDKProvider()
    outcome = await provider.stream(
        system="sys", user="user", model="claude-sonnet-4-6",
        max_tokens=100, on_token=on_token,
    )

    assert outcome.content == "reponse"
    assert recus == ["reponse"]


async def test_stream_sans_result_message_leve_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assistant = AssistantMessage(
        content=[TextBlock(text="sans fin")], model="claude-sonnet-4-6"
    )
    _patch_query(monkeypatch, [assistant])

    provider = ClaudeAgentSDKProvider()
    with pytest.raises(RuntimeError):
        await provider.stream(
            system="sys", user="user", model="claude-sonnet-4-6", max_tokens=100
        )
