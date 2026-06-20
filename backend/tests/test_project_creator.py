"""Tests TDD pour ProjectCreatorService — ticket-004."""
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from vibe_ide.models.project import ConversationMessage, CreateProjectResponse
from vibe_ide.models.ticket import TicketDraft, TicketPriority, TicketType
from vibe_ide.services.project_creator import ProjectCreatorService


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

_VALID_AGENT_JSON = json.dumps(
    {
        "project_id": "jardin-med",
        "name": "Potager Méditerranéen",
        "claude_md": "# Potager Méditerranéen\n\nProjet de planification de jardin.\n\n## Agents actifs\n\n- `orchestrateur`\n- `redacteur`\n- `planificateur`\n\n## Objectif\n\nPlanifier et suivre un potager méditerranéen.\n",
        "active_agents": ["orchestrateur", "redacteur", "planificateur"],
        "suggested_tickets": [
            {
                "title": "Définir la structure du jardin",
                "type": "feat",
                "priority": "high",
                "agent": "planificateur",
                "description": "Établir le plan d'ensemble du potager.",
            },
            {
                "title": "Liste des plantes méditerranéennes",
                "type": "docs",
                "priority": "medium",
                "agent": "redacteur",
                "description": "Recenser tomate, aubergine, courgette, basilic.",
            },
        ],
        "summary": "Projet de planification d'un potager méditerranéen.",
    }
)

_QUESTION_RESPONSE = (
    "Quel est le livrable principal de ce projet ? "
    "Un plan de plantation, un journal de suivi, ou autre chose ?"
)


def _make_client(response_text: str) -> MagicMock:
    mock = MagicMock()
    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text=response_text)]
    mock_resp.usage = MagicMock(
        input_tokens=100, output_tokens=50,
        cache_creation_input_tokens=0, cache_read_input_tokens=0,
    )
    mock.messages.create = AsyncMock(return_value=mock_resp)
    return mock


def _make_service(tmp_path: Path, response_text: str) -> ProjectCreatorService:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "project-creator.md").write_text(
        "Tu es le Project Creator.", encoding="utf-8"
    )
    workspace = tmp_path / "projects"
    workspace.mkdir()
    return ProjectCreatorService(
        client=_make_client(response_text),
        prompts_dir=prompts_dir,
        workspace_dir=workspace,
    )


def _user_message(content: str) -> ConversationMessage:
    return ConversationMessage(role="user", content=content)


# ------------------------------------------------------------------
# TicketDraft model
# ------------------------------------------------------------------


def test_ticket_draft_fields() -> None:
    draft = TicketDraft(
        title="Mon ticket",
        type=TicketType.feat,
        priority=TicketPriority.high,
        agent="codeur",
        description="Description.",
    )
    assert draft.title == "Mon ticket"
    assert draft.type == TicketType.feat
    assert draft.priority == TicketPriority.high
    assert draft.agent == "codeur"
    assert draft.description == "Description."


# ------------------------------------------------------------------
# One-shot : Claude retourne le JSON directement → projet créé
# ------------------------------------------------------------------


async def test_one_shot_creates_project(tmp_path: Path) -> None:
    svc = _make_service(tmp_path, _VALID_AGENT_JSON)
    result = await svc.create_project([_user_message("Je veux un potager méditerranéen")])

    assert result.done is True
    assert result.project is not None
    assert result.project.id == "jardin-med"
    assert result.project.name == "Potager Méditerranéen"


async def test_one_shot_returns_claude_md(tmp_path: Path) -> None:
    svc = _make_service(tmp_path, _VALID_AGENT_JSON)
    result = await svc.create_project([_user_message("Je veux un potager méditerranéen")])

    assert "Potager Méditerranéen" in result.claude_md_generated


async def test_one_shot_returns_suggested_tickets(tmp_path: Path) -> None:
    svc = _make_service(tmp_path, _VALID_AGENT_JSON)
    result = await svc.create_project([_user_message("Je veux un potager méditerranéen")])

    assert len(result.suggested_tickets) == 2
    assert result.suggested_tickets[0].title == "Définir la structure du jardin"
    assert result.suggested_tickets[0].type == TicketType.feat
    assert result.suggested_tickets[1].agent == "redacteur"


async def test_one_shot_project_exists_on_disk(tmp_path: Path) -> None:
    svc = _make_service(tmp_path, _VALID_AGENT_JSON)
    await svc.create_project([_user_message("Je veux un potager méditerranéen")])

    project_path = tmp_path / "projects" / "jardin-med"
    assert project_path.is_dir()
    assert (project_path / "CLAUDE.md").exists()


async def test_one_shot_uses_non_technical_agents(tmp_path: Path) -> None:
    """Un projet jardinage doit avoir des agents non-techniques (pas codeur)."""
    svc = _make_service(tmp_path, _VALID_AGENT_JSON)
    result = await svc.create_project([_user_message("Je veux un potager méditerranéen")])

    assert result.project is not None
    assert "codeur" not in result.project.active_agents


# ------------------------------------------------------------------
# Mode conversation : Claude pose des questions → pas encore de projet
# ------------------------------------------------------------------


async def test_conversation_returns_agent_message(tmp_path: Path) -> None:
    svc = _make_service(tmp_path, _QUESTION_RESPONSE)
    result = await svc.create_project([_user_message("Projet jardinage")])

    assert result.done is False
    assert result.project is None
    assert _QUESTION_RESPONSE in result.agent_message


async def test_conversation_no_project_created(tmp_path: Path) -> None:
    svc = _make_service(tmp_path, _QUESTION_RESPONSE)
    await svc.create_project([_user_message("Projet jardinage")])

    workspace = tmp_path / "projects"
    assert list(workspace.iterdir()) == []


# ------------------------------------------------------------------
# Conversation multi-tour : le projet est créé à la fin
# ------------------------------------------------------------------


async def test_multi_turn_creates_project(tmp_path: Path) -> None:
    svc = _make_service(tmp_path, _VALID_AGENT_JSON)
    conversation = [
        _user_message("Projet jardinage"),
        ConversationMessage(role="assistant", content=_QUESTION_RESPONSE),
        _user_message("Un plan de plantation et de suivi saisonnier."),
    ]
    result = await svc.create_project(conversation)

    assert result.done is True
    assert result.project is not None


# ------------------------------------------------------------------
# Sauvegarde du log de conversation
# ------------------------------------------------------------------


async def test_conversation_log_saved(tmp_path: Path) -> None:
    svc = _make_service(tmp_path, _VALID_AGENT_JSON)
    await svc.create_project([_user_message("Je veux un potager méditerranéen")])

    log_path = tmp_path / "projects" / "jardin-med" / "memory" / "project-creation-log.md"
    assert log_path.exists()
    content = log_path.read_text(encoding="utf-8")
    assert "potager méditerranéen" in content.lower()


# ------------------------------------------------------------------
# JSON embarqué dans du texte (ex : markdown code block)
# ------------------------------------------------------------------


async def test_json_in_markdown_code_block(tmp_path: Path) -> None:
    wrapped = f"Voici le projet :\n\n```json\n{_VALID_AGENT_JSON}\n```\n\nBonne continuation."
    svc = _make_service(tmp_path, wrapped)
    result = await svc.create_project([_user_message("Je veux un potager méditerranéen")])

    assert result.done is True
    assert result.project is not None
    assert result.project.id == "jardin-med"


# ------------------------------------------------------------------
# Appel Anthropic : vérification des paramètres
# ------------------------------------------------------------------


async def test_calls_anthropic_with_system_prompt(tmp_path: Path) -> None:
    svc = _make_service(tmp_path, _VALID_AGENT_JSON)
    await svc.create_project([_user_message("Projet test")])

    svc._client.messages.create.assert_called_once()
    kwargs = svc._client.messages.create.call_args.kwargs
    assert kwargs["system"][0]["text"] == "Tu es le Project Creator."


async def test_calls_anthropic_with_full_conversation(tmp_path: Path) -> None:
    svc = _make_service(tmp_path, _VALID_AGENT_JSON)
    conversation = [
        _user_message("Projet jardinage"),
        ConversationMessage(role="assistant", content="Quel type de projet ?"),
        _user_message("Un plan de plantation."),
    ]
    await svc.create_project(conversation)

    kwargs = svc._client.messages.create.call_args.kwargs
    assert len(kwargs["messages"]) == 3
    assert kwargs["messages"][0]["role"] == "user"
    assert kwargs["messages"][1]["role"] == "assistant"
    assert kwargs["messages"][2]["role"] == "user"


# ------------------------------------------------------------------
# Erreur : projet déjà existant
# ------------------------------------------------------------------


async def test_duplicate_project_raises(tmp_path: Path) -> None:
    svc = _make_service(tmp_path, _VALID_AGENT_JSON)
    await svc.create_project([_user_message("Je veux un potager méditerranéen")])

    with pytest.raises(ValueError, match="déjà existant"):
        await svc.create_project([_user_message("Je veux un potager méditerranéen")])
