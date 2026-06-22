"""Tests TDD pour ProjectCreatorService — ticket-004 + ticket-033."""
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

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

_BOOTSTRAP_PROMPT = "Tu es un agent dédié à ce projet."


def _make_client(response_text: str) -> MagicMock:
    mock = MagicMock()
    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text=response_text)]
    mock_resp.usage = MagicMock(
        input_tokens=100,
        output_tokens=50,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
    )
    mock.messages.create = AsyncMock(return_value=mock_resp)
    return mock


def _make_client_multi(responses: list[str]) -> MagicMock:
    """Client whose responses cycle through the given list."""
    mock = MagicMock()
    side_effects = []
    for text in responses:
        resp = MagicMock()
        resp.content = [MagicMock(text=text)]
        resp.usage = MagicMock(input_tokens=10, output_tokens=10)
        side_effects.append(resp)
    mock.messages.create = AsyncMock(side_effect=side_effects)
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


def _make_service_with_existing_agents(
    tmp_path: Path, response_text: str, existing_agents: list[str]
) -> ProjectCreatorService:
    """Service where specified agents already have prompt files."""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "project-creator.md").write_text(
        "Tu es le Project Creator.", encoding="utf-8"
    )
    for role in existing_agents:
        (prompts_dir / f"{role}.md").write_text(f"Prompt {role}.", encoding="utf-8")
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
# Appel Anthropic : vérification des paramètres (premier appel)
# ------------------------------------------------------------------


async def test_calls_anthropic_with_system_prompt(tmp_path: Path) -> None:
    svc = _make_service(tmp_path, _VALID_AGENT_JSON)
    await svc.create_project([_user_message("Projet test")])

    # Premier appel = création du projet (avec system prompt)
    first_call_kwargs = svc._client.messages.create.call_args_list[0].kwargs
    assert first_call_kwargs["system"][0]["text"] == "Tu es le Project Creator."


async def test_calls_anthropic_with_full_conversation(tmp_path: Path) -> None:
    svc = _make_service(tmp_path, _VALID_AGENT_JSON)
    conversation = [
        _user_message("Projet jardinage"),
        ConversationMessage(role="assistant", content="Quel type de projet ?"),
        _user_message("Un plan de plantation."),
    ]
    await svc.create_project(conversation)

    first_call_kwargs = svc._client.messages.create.call_args_list[0].kwargs
    assert len(first_call_kwargs["messages"]) == 3
    assert first_call_kwargs["messages"][0]["role"] == "user"
    assert first_call_kwargs["messages"][1]["role"] == "assistant"
    assert first_call_kwargs["messages"][2]["role"] == "user"


# ------------------------------------------------------------------
# Erreur : projet déjà existant
# ------------------------------------------------------------------


async def test_duplicate_project_raises(tmp_path: Path) -> None:
    svc = _make_service(tmp_path, _VALID_AGENT_JSON)
    await svc.create_project([_user_message("Je veux un potager méditerranéen")])

    with pytest.raises(ValueError, match="déjà existant"):
        await svc.create_project([_user_message("Je veux un potager méditerranéen")])


# ------------------------------------------------------------------
# ticket-033 — Auto-création des agents manquants
# ------------------------------------------------------------------


async def test_missing_agents_are_auto_created(tmp_path: Path) -> None:
    """Les agents absents du registre sont créés automatiquement."""
    svc = _make_service(tmp_path, _VALID_AGENT_JSON)
    result = await svc.create_project([_user_message("Je veux un potager méditerranéen")])

    prompts_dir = tmp_path / "prompts"
    # redacteur et planificateur ne sont pas builtins → doivent être créés
    assert (prompts_dir / "redacteur.md").exists()
    assert (prompts_dir / "planificateur.md").exists()
    assert result.agents_created == ["redacteur", "planificateur"]


async def test_existing_agents_not_recreated(tmp_path: Path) -> None:
    """Les agents déjà présents dans le registre ne sont pas recréés."""
    svc = _make_service_with_existing_agents(
        tmp_path, _VALID_AGENT_JSON, existing_agents=["redacteur", "planificateur"]
    )
    original_content = (tmp_path / "prompts" / "redacteur.md").read_text()

    result = await svc.create_project([_user_message("Je veux un potager méditerranéen")])

    # Contenu inchangé
    assert (tmp_path / "prompts" / "redacteur.md").read_text() == original_content
    assert result.agents_created == []


async def test_builtin_agents_not_bootstrapped(tmp_path: Path) -> None:
    """Les agents builtins (orchestrateur) ne déclenchent pas de bootstrap."""
    svc = _make_service_with_existing_agents(
        tmp_path, _VALID_AGENT_JSON, existing_agents=["redacteur", "planificateur"]
    )
    result = await svc.create_project([_user_message("Je veux un potager méditerranéen")])

    # orchestrateur est builtin → pas dans agents_created
    assert "orchestrateur" not in result.agents_created


async def test_agents_created_empty_when_all_exist(tmp_path: Path) -> None:
    """agents_created est vide si tous les agents existent déjà."""
    svc = _make_service_with_existing_agents(
        tmp_path,
        _VALID_AGENT_JSON,
        existing_agents=["redacteur", "planificateur"],
    )
    result = await svc.create_project([_user_message("Je veux un potager méditerranéen")])

    assert result.agents_created == []


async def test_bootstrap_uses_haiku_model(tmp_path: Path) -> None:
    """_bootstrap_agent utilise le modèle Haiku (coût faible)."""
    svc = _make_service(tmp_path, _VALID_AGENT_JSON)
    await svc.create_project([_user_message("Je veux un potager méditerranéen")])

    # Les appels de bootstrap (index 1 et 2) doivent utiliser Haiku
    from vibe_ide.services.project_creator import _BOOTSTRAP_MODEL

    bootstrap_calls = svc._client.messages.create.call_args_list[1:]
    for call in bootstrap_calls:
        assert call.kwargs["model"] == _BOOTSTRAP_MODEL


async def test_bootstrap_failure_does_not_block_creation(tmp_path: Path) -> None:
    """Un échec de bootstrap ne bloque pas la création du projet."""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "project-creator.md").write_text("Tu es le Project Creator.")
    workspace = tmp_path / "projects"
    workspace.mkdir()

    # Premier appel réussit, les suivants (bootstrap) lèvent une exception
    mock_client = MagicMock()
    success_resp = MagicMock()
    success_resp.content = [MagicMock(text=_VALID_AGENT_JSON)]
    success_resp.usage = MagicMock(input_tokens=10, output_tokens=10)
    mock_client.messages.create = AsyncMock(
        side_effect=[success_resp, RuntimeError("LLM down"), RuntimeError("LLM down")]
    )

    svc = ProjectCreatorService(
        client=mock_client, prompts_dir=prompts_dir, workspace_dir=workspace
    )
    result = await svc.create_project([_user_message("Je veux un potager méditerranéen")])

    assert result.done is True
    assert result.project is not None
    assert result.agents_created == []


async def test_conversation_with_no_active_agents_has_empty_agents_created(
    tmp_path: Path,
) -> None:
    """Quand done=False (conversation en cours), agents_created est vide."""
    svc = _make_service(tmp_path, _QUESTION_RESPONSE)
    result = await svc.create_project([_user_message("Projet jardinage")])

    assert result.done is False
    assert result.agents_created == []
