import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from vibe_ide.models.agent import AgentConfig, AgentResult, AgentRole
from vibe_ide.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from vibe_ide.services.agent_runner import AgentRunner, _parse_suggested_status


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


def _make_ticket(**kwargs: object) -> Ticket:
    defaults: dict[str, object] = {
        "id": "ticket-001",
        "title": "Implémenter la feature X",
        "type": TicketType.feat,
        "status": TicketStatus.todo,
        "priority": TicketPriority.medium,
        "agent": "codeur",
        "body": "## Description\nImplémenter la feature X.\n\n## Critères\n- [ ] Tests écrits",
    }
    return Ticket(**(defaults | kwargs))


def _mock_complete_client(response_text: str) -> MagicMock:
    """Client Anthropic mocké pour les appels non-streaming."""
    mock = MagicMock()
    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text=response_text)]
    mock_resp.usage = MagicMock(
        input_tokens=120,
        output_tokens=80,
        cache_creation_input_tokens=120,
        cache_read_input_tokens=0,
    )
    mock.messages.create = AsyncMock(return_value=mock_resp)
    return mock


def _runner(tmp_path: Path, client: MagicMock | None = None) -> AgentRunner:
    return AgentRunner(client or MagicMock(), tmp_path / "prompts")


# ------------------------------------------------------------------
# _parse_suggested_status
# ------------------------------------------------------------------


def test_parse_status_in_review() -> None:
    content = "## Analyse\nTout bon.\n\n## Statut suggéré\nIN_REVIEW — code prêt pour review"
    assert _parse_suggested_status(content) == TicketStatus.in_review


def test_parse_status_in_review_hyphen() -> None:
    assert _parse_suggested_status("## Statut suggéré\nIN-REVIEW") == TicketStatus.in_review


def test_parse_status_blocked() -> None:
    assert _parse_suggested_status("## Statut suggéré\nBLOCKED — besoin de précisions") == TicketStatus.blocked


def test_parse_status_done() -> None:
    assert _parse_suggested_status("## Statut suggéré\nDONE") == TicketStatus.done


def test_parse_status_todo() -> None:
    assert _parse_suggested_status("## Statut suggéré\nTODO") == TicketStatus.todo


def test_parse_status_default_when_absent() -> None:
    assert _parse_suggested_status("Réponse sans section statut.") == TicketStatus.in_review


def test_parse_status_accent_insensitive() -> None:
    content = "## Statut suggere\nIN_REVIEW"
    assert _parse_suggested_status(content) == TicketStatus.in_review


# ------------------------------------------------------------------
# _load_system_prompt
# ------------------------------------------------------------------


def test_load_system_prompt_reads_file(tmp_path: Path) -> None:
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "codeur.md").write_text("Tu es le codeur.", encoding="utf-8")

    runner = AgentRunner(MagicMock(), prompts)
    assert runner._load_system_prompt(AgentRole.codeur) == "Tu es le codeur."


def test_load_system_prompt_fallback_when_missing(tmp_path: Path) -> None:
    runner = _runner(tmp_path)  # prompts dir doesn't exist
    prompt = runner._load_system_prompt(AgentRole.codeur)
    assert "codeur" in prompt.lower()
    assert len(prompt) > 10


# ------------------------------------------------------------------
# _build_user_prompt
# ------------------------------------------------------------------


def test_build_user_prompt_contains_ticket_body(tmp_path: Path) -> None:
    runner = _runner(tmp_path)
    ticket = _make_ticket(body="Corps du ticket précis.")

    prompt = runner._build_user_prompt(ticket, AgentRole.codeur, "contexte projet")

    assert "Corps du ticket précis." in prompt
    assert "contexte projet" in prompt


def test_build_user_prompt_has_required_sections(tmp_path: Path) -> None:
    runner = _runner(tmp_path)
    prompt = runner._build_user_prompt(_make_ticket(), AgentRole.codeur, "ctx")

    assert "## Contexte projet" in prompt
    assert "## Ticket assigné" in prompt
    assert "## Ta mission" in prompt


def test_build_user_prompt_instruction_varies_by_role(tmp_path: Path) -> None:
    runner = _runner(tmp_path)
    ticket = _make_ticket()

    codeur_prompt = runner._build_user_prompt(ticket, AgentRole.codeur, "ctx")
    reviewer_prompt = runner._build_user_prompt(ticket, AgentRole.reviewer, "ctx")

    assert codeur_prompt != reviewer_prompt


# ------------------------------------------------------------------
# AgentRunner.run — non-streaming (mocked client)
# ------------------------------------------------------------------


async def test_run_returns_agent_result(tmp_path: Path) -> None:
    response = "## Analyse\nOK.\n\n## Statut suggéré\nIN_REVIEW"
    client = _mock_complete_client(response)
    runner = AgentRunner(client, tmp_path / "prompts")

    result = await runner.run(
        role=AgentRole.codeur,
        ticket=_make_ticket(),
        project_context="Contexte test",
    )

    assert isinstance(result, AgentResult)
    assert result.ticket_id == "ticket-001"
    assert result.role == AgentRole.codeur
    assert result.suggested_status == TicketStatus.in_review
    assert result.duration_ms >= 0
    assert result.content == response


async def test_run_calls_anthropic_create(tmp_path: Path) -> None:
    client = _mock_complete_client("## Statut suggéré\nIN_REVIEW")
    runner = AgentRunner(client, tmp_path / "prompts")

    await runner.run(
        role=AgentRole.codeur,
        ticket=_make_ticket(),
        project_context="ctx",
    )

    client.messages.create.assert_called_once()
    kwargs = client.messages.create.call_args.kwargs
    assert kwargs["model"] == "claude-sonnet-4-6"
    assert kwargs["max_tokens"] == 8192


async def test_run_uses_agent_config_model(tmp_path: Path) -> None:
    client = _mock_complete_client("## Statut suggéré\nIN_REVIEW")
    runner = AgentRunner(client, tmp_path / "prompts")
    cfg = AgentConfig(
        role="codeur",
        model="claude-opus-4-8",
        max_tokens=16000,
        prompt_file="agents/prompts/codeur.md",
    )

    await runner.run(
        role=AgentRole.codeur,
        ticket=_make_ticket(),
        project_context="ctx",
        agent_config=cfg,
    )

    kwargs = client.messages.create.call_args.kwargs
    assert kwargs["model"] == "claude-opus-4-8"
    assert kwargs["max_tokens"] == 16000


async def test_run_enables_prompt_caching(tmp_path: Path) -> None:
    client = _mock_complete_client("## Statut suggéré\nIN_REVIEW")
    runner = AgentRunner(client, tmp_path / "prompts")

    await runner.run(
        role=AgentRole.codeur,
        ticket=_make_ticket(),
        project_context="ctx",
    )

    kwargs = client.messages.create.call_args.kwargs
    system = kwargs["system"]
    assert any(
        block.get("cache_control", {}).get("type") == "ephemeral"
        for block in system
    )


# ------------------------------------------------------------------
# AgentRunner.run — streaming (mocked client)
# ------------------------------------------------------------------


async def test_run_calls_stream_callback(tmp_path: Path) -> None:
    tokens: list[str] = []

    async def capture(token: str) -> None:
        tokens.append(token)

    # Construire un mock de context manager async pour stream()
    mock_stream = MagicMock()

    async def _text_stream():  # type: ignore[return]
        for t in ["Bonjour", " monde"]:
            yield t

    mock_stream.text_stream = _text_stream()

    full_text = "Bonjour monde\n\n## Statut suggéré\nIN_REVIEW"
    final_msg = MagicMock()
    final_msg.content = [MagicMock(text=full_text)]
    final_msg.usage = MagicMock(
        input_tokens=10, output_tokens=5,
        cache_creation_input_tokens=0, cache_read_input_tokens=0,
    )
    mock_stream.get_final_message = AsyncMock(return_value=final_msg)

    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_stream)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)

    client = MagicMock()
    client.messages.stream = MagicMock(return_value=mock_ctx)

    runner = AgentRunner(client, tmp_path / "prompts")
    result = await runner.run(
        role=AgentRole.codeur,
        ticket=_make_ticket(),
        project_context="ctx",
        stream_callback=capture,
    )

    assert tokens == ["Bonjour", " monde"]
    assert "Bonjour monde" in result.content


# ------------------------------------------------------------------
# Test d'intégration (API réelle — skippé si clé dummy)
# ------------------------------------------------------------------


@pytest.mark.integration
async def test_run_real_api(tmp_path: Path) -> None:
    """Nécessite une vraie ANTHROPIC_API_KEY (pas 'dummy')."""
    from anthropic import AsyncAnthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "dummy":
        pytest.skip("ANTHROPIC_API_KEY non disponible pour le test d'intégration")

    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "codeur.md").write_text(
        "Tu es un agent de test. Réponds en 30 mots maximum.", encoding="utf-8"
    )

    client = AsyncAnthropic(api_key=api_key)
    runner = AgentRunner(client, prompts)
    ticket = _make_ticket(body="Dis bonjour en Python avec print().")

    result = await runner.run(
        role=AgentRole.codeur,
        ticket=ticket,
        project_context="Projet de test minimal.",
    )

    assert result.content
    assert result.duration_ms > 0
    assert isinstance(result.suggested_status, TicketStatus)
