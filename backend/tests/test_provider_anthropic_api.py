from unittest.mock import AsyncMock, MagicMock

import pytest

from tessera.services.providers.anthropic_api import AnthropicApiProvider


def _mock_client(text: str = "réponse") -> MagicMock:
    mock = MagicMock()
    resp = MagicMock()
    resp.content = [MagicMock(text=text)]
    resp.usage = MagicMock(
        input_tokens=120,
        output_tokens=80,
        cache_creation_input_tokens=30,
        cache_read_input_tokens=10,
    )
    mock.messages.create = AsyncMock(return_value=resp)
    return mock


def test_nom_du_provider() -> None:
    assert AnthropicApiProvider(_mock_client()).name == "anthropic_api"


@pytest.mark.asyncio
async def test_complete_renvoie_contenu_et_tokens() -> None:
    provider = AnthropicApiProvider(_mock_client("bonjour"))
    result = await provider.complete(
        system="sys", user="usr", model="claude-sonnet-4-6", max_tokens=1000
    )
    assert result.content == "bonjour"
    assert result.input_tokens == 120
    assert result.output_tokens == 80
    assert result.cache_read_tokens == 10
    assert result.cache_creation_tokens == 30
    assert result.cost_usd is None
    assert result.provider_name == "anthropic_api"


@pytest.mark.asyncio
async def test_complete_passe_le_cache_control_sur_le_system() -> None:
    client = _mock_client()
    provider = AnthropicApiProvider(client)
    await provider.complete(
        system="mon prompt", user="usr", model="claude-sonnet-4-6", max_tokens=1000
    )
    kwargs = client.messages.create.call_args.kwargs
    assert kwargs["model"] == "claude-sonnet-4-6"
    assert kwargs["max_tokens"] == 1000
    assert kwargs["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert kwargs["system"][0]["text"] == "mon prompt"
    assert kwargs["messages"] == [{"role": "user", "content": "usr"}]


@pytest.mark.asyncio
async def test_complete_avec_system_vide_n_envoie_aucun_bloc_system() -> None:
    """Regression — ticket-044 review, finding 3.

    An empty ``system`` must not produce ``[{"type": "text", "text": ""}]``:
    the Messages API rejects empty text blocks with a 400. ``project_creator``
    calls ``complete(system="", ...)`` for the bootstrap-agent prompt, so this
    must degrade to "no system block" instead of raising.
    """
    client = _mock_client()
    provider = AnthropicApiProvider(client)
    await provider.complete(system="", user="usr", model="claude-sonnet-4-6", max_tokens=1000)
    kwargs = client.messages.create.call_args.kwargs
    assert kwargs["system"] == []


@pytest.mark.asyncio
async def test_complete_avec_system_blanc_n_envoie_aucun_bloc_system() -> None:
    """Whitespace-only system strings must also degrade to no system block."""
    client = _mock_client()
    provider = AnthropicApiProvider(client)
    await provider.complete(system="   \n", user="usr", model="claude-sonnet-4-6", max_tokens=1000)
    kwargs = client.messages.create.call_args.kwargs
    assert kwargs["system"] == []


@pytest.mark.asyncio
async def test_complete_avec_system_non_vide_conserve_le_bloc_cache() -> None:
    """A non-empty system string still yields today's single cached text block."""
    client = _mock_client()
    provider = AnthropicApiProvider(client)
    await provider.complete(
        system="mon prompt", user="usr", model="claude-sonnet-4-6", max_tokens=1000
    )
    kwargs = client.messages.create.call_args.kwargs
    assert kwargs["system"] == [
        {"type": "text", "text": "mon prompt", "cache_control": {"type": "ephemeral"}}
    ]


@pytest.mark.asyncio
async def test_complete_ignore_les_blocs_sans_texte() -> None:
    client = _mock_client()
    bloc_sans_texte = MagicMock(spec=[])
    client.messages.create.return_value.content = [
        bloc_sans_texte,
        MagicMock(text="visible"),
    ]
    provider = AnthropicApiProvider(client)
    result = await provider.complete(
        system="sys", user="usr", model="claude-sonnet-4-6", max_tokens=1000
    )
    assert result.content == "visible"


class _MockAsyncStream:
    """Mock async context manager for stream() testing."""

    def __init__(self, chunks: list[str]) -> None:
        self.chunks = chunks
        self._final_message = MagicMock(
            usage=MagicMock(
                input_tokens=120,
                output_tokens=80,
                cache_creation_input_tokens=30,
                cache_read_input_tokens=10,
            )
        )

    async def __aenter__(self) -> "_MockAsyncStream":
        return self

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        pass

    @property
    def text_stream(self) -> "AsyncIteratorMock":
        return AsyncIteratorMock(self.chunks)

    async def get_final_message(self) -> MagicMock:
        return self._final_message


class AsyncIteratorMock:
    """Mock async iterator for stream chunks."""

    def __init__(self, chunks: list[str]) -> None:
        self.chunks = chunks
        self._index = 0

    def __aiter__(self) -> "AsyncIteratorMock":
        return self

    async def __anext__(self) -> str:
        if self._index >= len(self.chunks):
            raise StopAsyncIteration
        chunk = self.chunks[self._index]
        self._index += 1
        return chunk


@pytest.mark.asyncio
async def test_stream_accumule_le_contenu_des_chunks() -> None:
    client = MagicMock()
    client.messages.stream = MagicMock(
        return_value=_MockAsyncStream(["hello", " ", "world"])
    )
    provider = AnthropicApiProvider(client)
    result = await provider.stream(
        system="sys", user="usr", model="claude-sonnet-4-6", max_tokens=1000
    )
    assert result.content == "hello world"


@pytest.mark.asyncio
async def test_stream_appelle_on_token_pour_chaque_chunk() -> None:
    client = MagicMock()
    client.messages.stream = MagicMock(
        return_value=_MockAsyncStream(["a", "b", "c"])
    )
    provider = AnthropicApiProvider(client)
    on_token = AsyncMock()
    await provider.stream(
        system="sys",
        user="usr",
        model="claude-sonnet-4-6",
        max_tokens=1000,
        on_token=on_token,
    )
    assert on_token.call_count == 3
    on_token.assert_any_call("a")
    on_token.assert_any_call("b")
    on_token.assert_any_call("c")


@pytest.mark.asyncio
async def test_stream_renvoie_tokens_et_provider_name() -> None:
    client = MagicMock()
    client.messages.stream = MagicMock(
        return_value=_MockAsyncStream(["content"])
    )
    provider = AnthropicApiProvider(client)
    result = await provider.stream(
        system="sys", user="usr", model="claude-sonnet-4-6", max_tokens=1000
    )
    assert result.input_tokens == 120
    assert result.output_tokens == 80
    assert result.cache_read_tokens == 10
    assert result.cache_creation_tokens == 30
    assert result.provider_name == "anthropic_api"


@pytest.mark.asyncio
async def test_stream_passe_les_kwargs_corrects_a_messages_stream() -> None:
    client = MagicMock()
    client.messages.stream = MagicMock(
        return_value=_MockAsyncStream(["text"])
    )
    provider = AnthropicApiProvider(client)
    await provider.stream(
        system="mon prompt",
        user="contenu utilisateur",
        model="claude-sonnet-4-6",
        max_tokens=1000,
    )
    kwargs = client.messages.stream.call_args.kwargs
    assert kwargs["model"] == "claude-sonnet-4-6"
    assert kwargs["max_tokens"] == 1000
    assert kwargs["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert kwargs["system"][0]["text"] == "mon prompt"
    assert kwargs["messages"] == [{"role": "user", "content": "contenu utilisateur"}]


@pytest.mark.asyncio
async def test_stream_ignore_cwd_et_on_tool_use() -> None:
    from pathlib import Path

    client = MagicMock()
    client.messages.stream = MagicMock(
        return_value=_MockAsyncStream(["text"])
    )
    provider = AnthropicApiProvider(client)
    on_tool_use = AsyncMock()
    result = await provider.stream(
        system="sys",
        user="usr",
        model="claude-sonnet-4-6",
        max_tokens=1000,
        cwd=Path("/some/path"),
        on_tool_use=on_tool_use,
    )
    # Assert the exact kwarg set reaching messages.stream — this fails if
    # `cwd` (or any other unexpected key) were ever forwarded, unlike the
    # previous `"cwd" not in kwargs` assertion which held unconditionally
    # regardless of what the provider actually forwarded.
    kwargs = client.messages.stream.call_args.kwargs
    assert set(kwargs) == {"model", "max_tokens", "system", "messages"}
    assert kwargs["model"] == "claude-sonnet-4-6"
    assert kwargs["max_tokens"] == 1000
    assert kwargs["messages"] == [{"role": "user", "content": "usr"}]
    # AnthropicApiProvider has no tool-use events of its own to report:
    # on_tool_use must never be awaited.
    on_tool_use.assert_not_awaited()
    assert result.content == "text"
    assert result.provider_name == "anthropic_api"
