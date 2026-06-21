"""Tests TDD pour AgentCreatorService — ticket-023."""
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from vibe_ide.models.agent import CreateAgentConversationResponse
from vibe_ide.models.project import ConversationMessage
from vibe_ide.services.agent_creator import AgentCreatorService


# ------------------------------------------------------------------
# Constants / helpers
# ------------------------------------------------------------------

_VALID_AGENT_JSON = json.dumps(
    {
        "role": "redacteur",
        "description": "Rédige des textes clairs et engageants",
        "system_prompt": "Tu es un rédacteur professionnel. Tu produis des textes clairs, concis et engageants.",
    }
)

_QUESTION_RESPONSE = (
    "Pour créer le meilleur agent possible, j'ai besoin de précisions :\n"
    "- Quel type de contenu cet agent va-t-il produire ?\n"
    "- Y a-t-il un ton particulier à respecter ?"
)


def _make_mock_client(response_text: str) -> MagicMock:
    mock = MagicMock()
    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text=response_text)]
    mock_resp.usage = MagicMock(input_tokens=50, output_tokens=30)
    mock.messages.create = AsyncMock(return_value=mock_resp)
    return mock


def _make_service(tmp_path: Path, response_text: str) -> AgentCreatorService:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "agent-creator.md").write_text(
        "Tu es un expert en prompt engineering.", encoding="utf-8"
    )
    return AgentCreatorService(
        client=_make_mock_client(response_text),
        prompts_dir=prompts_dir,
    )


def _user(content: str) -> ConversationMessage:
    return ConversationMessage(role="user", content=content)


# ------------------------------------------------------------------
# JSON valide → agent créé
# ------------------------------------------------------------------


async def test_create_agent_returns_created_true(tmp_path: Path) -> None:
    svc = _make_service(tmp_path, _VALID_AGENT_JSON)
    result = await svc.create_agent([_user("Je veux un agent rédacteur")])
    assert result.created is True


async def test_create_agent_returns_role(tmp_path: Path) -> None:
    svc = _make_service(tmp_path, _VALID_AGENT_JSON)
    result = await svc.create_agent([_user("Je veux un agent rédacteur")])
    assert result.agent is not None
    assert result.agent.role == "redacteur"


async def test_create_agent_returns_description(tmp_path: Path) -> None:
    svc = _make_service(tmp_path, _VALID_AGENT_JSON)
    result = await svc.create_agent([_user("Je veux un agent rédacteur")])
    assert result.agent is not None
    assert result.agent.description == "Rédige des textes clairs et engageants"


async def test_create_agent_persists_prompt_file(tmp_path: Path) -> None:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "agent-creator.md").write_text("prompt", encoding="utf-8")
    svc = AgentCreatorService(client=_make_mock_client(_VALID_AGENT_JSON), prompts_dir=prompts_dir)
    await svc.create_agent([_user("Je veux un agent rédacteur")])
    assert (prompts_dir / "redacteur.md").exists()


async def test_create_agent_prompt_file_content(tmp_path: Path) -> None:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "agent-creator.md").write_text("prompt", encoding="utf-8")
    svc = AgentCreatorService(client=_make_mock_client(_VALID_AGENT_JSON), prompts_dir=prompts_dir)
    await svc.create_agent([_user("Je veux un agent rédacteur")])
    content = (prompts_dir / "redacteur.md").read_text(encoding="utf-8")
    assert "rédacteur professionnel" in content


# ------------------------------------------------------------------
# Réponse vague → clarification
# ------------------------------------------------------------------


async def test_clarification_returns_created_false(tmp_path: Path) -> None:
    svc = _make_service(tmp_path, _QUESTION_RESPONSE)
    result = await svc.create_agent([_user("Un agent")])
    assert result.created is False


async def test_clarification_returns_no_agent(tmp_path: Path) -> None:
    svc = _make_service(tmp_path, _QUESTION_RESPONSE)
    result = await svc.create_agent([_user("Un agent")])
    assert result.agent is None


async def test_clarification_returns_message(tmp_path: Path) -> None:
    svc = _make_service(tmp_path, _QUESTION_RESPONSE)
    result = await svc.create_agent([_user("Un agent")])
    assert _QUESTION_RESPONSE in result.message


async def test_clarification_does_not_persist_file(tmp_path: Path) -> None:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "agent-creator.md").write_text("prompt", encoding="utf-8")
    svc = AgentCreatorService(client=_make_mock_client(_QUESTION_RESPONSE), prompts_dir=prompts_dir)
    await svc.create_agent([_user("Un agent vague")])
    md_files = [f for f in prompts_dir.glob("*.md") if f.name != "agent-creator.md"]
    assert len(md_files) == 0


# ------------------------------------------------------------------
# JSON incomplet → clarification
# ------------------------------------------------------------------


async def test_json_without_role_returns_clarification(tmp_path: Path) -> None:
    incomplete = json.dumps({"description": "un agent", "system_prompt": "..."})
    svc = _make_service(tmp_path, incomplete)
    result = await svc.create_agent([_user("Un agent")])
    assert result.created is False


async def test_json_without_system_prompt_returns_clarification(tmp_path: Path) -> None:
    incomplete = json.dumps({"role": "redacteur", "description": "..."})
    svc = _make_service(tmp_path, incomplete)
    result = await svc.create_agent([_user("Un agent")])
    assert result.created is False


# ------------------------------------------------------------------
# JSON dans un bloc markdown → extraction correcte
# ------------------------------------------------------------------


async def test_json_wrapped_in_markdown_code_block(tmp_path: Path) -> None:
    wrapped = f"Voici l'agent :\n\n```json\n{_VALID_AGENT_JSON}\n```"
    svc = _make_service(tmp_path, wrapped)
    result = await svc.create_agent([_user("Un rédacteur")])
    assert result.created is True
    assert result.agent is not None
    assert result.agent.role == "redacteur"


# ------------------------------------------------------------------
# Appel Anthropic
# ------------------------------------------------------------------


async def test_calls_anthropic_with_system_prompt(tmp_path: Path) -> None:
    svc = _make_service(tmp_path, _VALID_AGENT_JSON)
    await svc.create_agent([_user("Un rédacteur")])
    svc._client.messages.create.assert_called_once()
    kwargs = svc._client.messages.create.call_args.kwargs
    assert kwargs["system"][0]["text"] == "Tu es un expert en prompt engineering."


async def test_calls_anthropic_with_full_conversation(tmp_path: Path) -> None:
    svc = _make_service(tmp_path, _VALID_AGENT_JSON)
    conversation = [
        _user("Je veux un rédacteur"),
        ConversationMessage(role="assistant", content="Quel type de contenu ?"),
        _user("Des articles de blog."),
    ]
    await svc.create_agent(conversation)
    kwargs = svc._client.messages.create.call_args.kwargs
    assert len(kwargs["messages"]) == 3
    assert kwargs["messages"][0]["role"] == "user"
    assert kwargs["messages"][1]["role"] == "assistant"
    assert kwargs["messages"][2]["role"] == "user"


# ------------------------------------------------------------------
# Fallback sans fichier agent-creator.md
# ------------------------------------------------------------------


async def test_missing_system_prompt_uses_fallback(tmp_path: Path) -> None:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    svc = AgentCreatorService(client=_make_mock_client(_VALID_AGENT_JSON), prompts_dir=prompts_dir)
    result = await svc.create_agent([_user("Un rédacteur")])
    assert result.created is True


# ------------------------------------------------------------------
# Conversation multi-tour
# ------------------------------------------------------------------


async def test_multi_turn_creates_agent(tmp_path: Path) -> None:
    svc = _make_service(tmp_path, _VALID_AGENT_JSON)
    conversation = [
        _user("Je veux un agent"),
        ConversationMessage(role="assistant", content=_QUESTION_RESPONSE),
        _user("Des articles de blog, ton décontracté."),
    ]
    result = await svc.create_agent(conversation)
    assert result.created is True
