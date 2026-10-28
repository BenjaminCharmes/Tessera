"""Structured output through the three providers — ticket-612 (ADR-061)."""
import json
from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import respx
from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock, ToolUseBlock

import tessera.services.providers.agent_sdk as agent_sdk_module
from tessera.services.providers.agent_sdk import ClaudeAgentSDKProvider, _build_options
from tessera.services.providers.anthropic_api import OUTIL_SORTIE, AnthropicApiProvider
from tessera.services.providers.base import ProviderResult
from tessera.services.providers.ollama import OllamaProvider, _reset_cooldowns

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"verdict": {"type": "string"}},
    "required": ["verdict"],
}
_BASE = "http://ollama.test:11434"


def test_provider_result_structured_vaut_none_par_defaut() -> None:
    assert ProviderResult(content="x").structured is None


# --- Agent SDK ---


def _resultat_sdk(subtype: str = "success", structured: Any = None) -> ResultMessage:
    return ResultMessage(
        subtype=subtype, duration_ms=1, duration_api_ms=1, is_error=False,
        num_turns=1, session_id="s", structured_output=structured,
    )


def _patch_query(
    monkeypatch: pytest.MonkeyPatch, messages: list[Any], vues: list[Any] | None = None
) -> None:
    async def fake_query(*, prompt: str, options: Any) -> AsyncIterator[Any]:
        if vues is not None:
            vues.append(options)
        for message in messages:
            yield message

    monkeypatch.setattr(agent_sdk_module, "query", fake_query)


async def _complete_sdk(schema: dict[str, Any] | None) -> ProviderResult:
    kw: dict[str, Any] = {} if schema is None else {"schema": schema}
    return await ClaudeAgentSDKProvider().complete(
        system="s", user="u", model="m", max_tokens=10, **kw
    )


async def test_sdk_rend_la_sortie_structuree_et_pose_output_format(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    vues: list[Any] = []
    _patch_query(monkeypatch, [_resultat_sdk(structured={"verdict": "OK"})], vues)

    resultat = await _complete_sdk(SCHEMA)

    assert resultat.structured == {"verdict": "OK"}
    assert vues[0].output_format == {"type": "json_schema", "schema": SCHEMA}


async def test_sdk_sans_schema_ne_pose_pas_output_format(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    vues: list[Any] = []
    _patch_query(monkeypatch, [_resultat_sdk()], vues)

    resultat = await _complete_sdk(None)

    assert vues[0].output_format is None
    assert resultat.structured is None


def test_build_options_sans_schema_laisse_output_format_vide() -> None:
    options = _build_options(
        system="s", model="m", max_turns=1, max_budget_usd=None, cwd=None
    )
    assert options.output_format is None


async def test_sdk_success_sans_structured_output_rend_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_query(monkeypatch, [_resultat_sdk("success", None)])
    assert (await _complete_sdk(SCHEMA)).structured is None


async def test_sdk_echec_des_relances_rend_none(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_query(
        monkeypatch,
        [_resultat_sdk("error_max_structured_output_retries", {"verdict": "OK"})],
    )
    assert (await _complete_sdk(SCHEMA)).structured is None


async def test_sdk_un_bloc_structured_output_ne_part_pas_dans_on_tool_use(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assistant = AssistantMessage(
        content=[
            ToolUseBlock(id="1", name="Read", input={"file_path": "a"}),
            ToolUseBlock(id="2", name="StructuredOutput", input={"verdict": "OK"}),
        ],
        model="m",
    )
    _patch_query(monkeypatch, [assistant, _resultat_sdk(structured={"verdict": "OK"})])
    on_tool_use = AsyncMock()

    resultat = await ClaudeAgentSDKProvider().stream(
        system="s", user="u", model="m", max_tokens=10,
        on_tool_use=on_tool_use, schema=SCHEMA,
    )

    on_tool_use.assert_awaited_once_with("Read", {"file_path": "a"})
    assert resultat.structured == {"verdict": "OK"}


async def test_sdk_stream_garde_le_texte_dans_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assistant = AssistantMessage(content=[TextBlock(text="texte")], model="m")
    _patch_query(monkeypatch, [assistant, _resultat_sdk(structured={"verdict": "OK"})])
    resultat = await ClaudeAgentSDKProvider().stream(
        system="s", user="u", model="m", max_tokens=10, schema=SCHEMA
    )
    assert resultat.content == "texte"


# --- API Anthropic ---


def _client(content: list[Any]) -> MagicMock:
    client = MagicMock()
    reponse = MagicMock(content=content, usage=MagicMock(input_tokens=1, output_tokens=2))
    client.messages.create = AsyncMock(return_value=reponse)
    return client


def _tool_use(entree: Any) -> SimpleNamespace:
    return SimpleNamespace(type="tool_use", name=OUTIL_SORTIE, input=entree)


async def test_anthropic_complete_force_l_outil_et_lit_son_input() -> None:
    client = _client([_tool_use({"verdict": "OK"})])
    resultat = await AnthropicApiProvider(client).complete(
        system="s", user="u", model="m", max_tokens=10, schema=SCHEMA
    )
    kwargs = client.messages.create.call_args.kwargs
    assert kwargs["tools"][0]["name"] == OUTIL_SORTIE
    assert kwargs["tools"][0]["input_schema"] == SCHEMA
    assert kwargs["tool_choice"] == {"type": "tool", "name": OUTIL_SORTIE}
    assert resultat.structured == {"verdict": "OK"}


async def test_anthropic_complete_sans_schema_n_ajoute_aucun_outil() -> None:
    client = _client([MagicMock(text="x")])
    resultat = await AnthropicApiProvider(client).complete(
        system="s", user="u", model="m", max_tokens=10
    )
    assert set(client.messages.create.call_args.kwargs) == {
        "model", "max_tokens", "system", "messages"
    }
    assert resultat.structured is None


async def test_anthropic_sans_bloc_tool_use_rend_none() -> None:
    client = _client([MagicMock(text="du texte")])
    resultat = await AnthropicApiProvider(client).complete(
        system="s", user="u", model="m", max_tokens=10, schema=SCHEMA
    )
    assert resultat.structured is None


async def test_anthropic_stream_lit_l_input_du_message_final() -> None:
    from tests.test_provider_anthropic_api import _MockAsyncStream

    flux = _MockAsyncStream([])
    flux._final_message.content = [_tool_use({"verdict": "OK"})]
    client = MagicMock()
    client.messages.stream = MagicMock(return_value=flux)

    resultat = await AnthropicApiProvider(client).stream(
        system="s", user="u", model="m", max_tokens=10, schema=SCHEMA
    )

    assert client.messages.stream.call_args.kwargs["tool_choice"]["name"] == OUTIL_SORTIE
    assert resultat.structured == {"verdict": "OK"}


# --- Ollama ---


@pytest.fixture(autouse=True)
def _remise_a_zero() -> None:
    _reset_cooldowns()


def _reponse(contenu: str, **plus: Any) -> dict[str, Any]:
    return {
        "message": {"role": "assistant", "content": contenu},
        "done": True, "prompt_eval_count": 1, "eval_count": 1, **plus,
    }


def _mock_ollama(corps: dict[str, Any]) -> respx.Route:
    tags = {"models": [{"name": "q"}]}
    respx.get(f"{_BASE}/api/tags").mock(return_value=httpx.Response(200, json=tags))
    return respx.post(f"{_BASE}/api/chat").mock(return_value=httpx.Response(200, json=corps))


@respx.mock
async def test_ollama_envoie_format_et_parse_le_contenu() -> None:
    route = _mock_ollama(_reponse('{"verdict": "OK"}'))
    resultat = await OllamaProvider(_BASE).complete(
        system="s", user="u", model="q", max_tokens=10, schema=SCHEMA
    )
    assert json.loads(route.calls[0].request.content)["format"] == SCHEMA
    assert resultat.structured == {"verdict": "OK"}


@respx.mock
async def test_ollama_sans_schema_n_envoie_pas_format() -> None:
    route = _mock_ollama(_reponse('{"verdict": "OK"}'))
    resultat = await OllamaProvider(_BASE).complete(
        system="s", user="u", model="q", max_tokens=10
    )
    assert "format" not in json.loads(route.calls[0].request.content)
    assert resultat.structured is None


@respx.mock
@pytest.mark.parametrize(
    ("contenu", "plus"),
    [
        ('{"verdict": "O', {}),
        ('{"verdict": "OK"}', {"done_reason": "length"}),
        ("[1, 2]", {}),
    ],
)
async def test_ollama_json_tronque_ou_invalide_rend_none(
    contenu: str, plus: dict[str, Any]
) -> None:
    _mock_ollama(_reponse(contenu, **plus))
    resultat = await OllamaProvider(_BASE).complete(
        system="s", user="u", model="q", max_tokens=10, schema=SCHEMA
    )
    assert resultat.structured is None
    assert resultat.content == contenu


@respx.mock
async def test_ollama_stream_assemble_le_json_des_fragments() -> None:
    tags = {"models": [{"name": "q"}]}
    respx.get(f"{_BASE}/api/tags").mock(return_value=httpx.Response(200, json=tags))
    lignes = [
        {"message": {"content": '{"verdict":'}, "done": False},
        _reponse(' "OK"}'),
    ]
    respx.post(f"{_BASE}/api/chat").mock(
        return_value=httpx.Response(200, content="\n".join(json.dumps(x) for x in lignes))
    )
    resultat = await OllamaProvider(_BASE).stream(
        system="s", user="u", model="q", max_tokens=10, schema=SCHEMA
    )
    assert resultat.structured == {"verdict": "OK"}
