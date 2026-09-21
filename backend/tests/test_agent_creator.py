"""TDD tests for AgentCreatorService — ticket-023."""
import json
from pathlib import Path

import pytest

from tessera.services.prompt_loader import MissingPromptError

from tests.test_providers_base import FakeProvider
from tessera.models.agent import CreateAgentConversationResponse
from tessera.models.project import ConversationMessage
from tessera.services.agent_creator import AgentCreatorService


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


def _make_provider(response_text: str) -> FakeProvider:
    return FakeProvider(content=response_text)


def _make_service(tmp_path: Path, response_text: str) -> AgentCreatorService:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "agent-creator.md").write_text(
        "Tu es un expert en prompt engineering.", encoding="utf-8"
    )
    return AgentCreatorService(
        provider=_make_provider(response_text),
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
    svc = AgentCreatorService(provider=_make_provider(_VALID_AGENT_JSON), prompts_dir=prompts_dir)
    await svc.create_agent([_user("Je veux un agent rédacteur")])
    assert (prompts_dir / "redacteur.md").exists()


async def test_create_agent_prompt_file_content(tmp_path: Path) -> None:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "agent-creator.md").write_text("prompt", encoding="utf-8")
    svc = AgentCreatorService(provider=_make_provider(_VALID_AGENT_JSON), prompts_dir=prompts_dir)
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
    svc = AgentCreatorService(provider=_make_provider(_QUESTION_RESPONSE), prompts_dir=prompts_dir)
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
# Appel au provider
# ------------------------------------------------------------------


async def test_calls_provider_with_system_prompt(tmp_path: Path) -> None:
    svc = _make_service(tmp_path, _VALID_AGENT_JSON)
    await svc.create_agent([_user("Un rédacteur")])
    provider = svc._provider
    assert len(provider.calls) == 1
    assert provider.calls[0]["system"] == "Tu es un expert en prompt engineering."


async def test_calls_provider_with_full_conversation(tmp_path: Path) -> None:
    svc = _make_service(tmp_path, _VALID_AGENT_JSON)
    conversation = [
        _user("Je veux un rédacteur"),
        ConversationMessage(role="assistant", content="Quel type de contenu ?"),
        _user("Des articles de blog."),
    ]
    await svc.create_agent(conversation)
    provider = svc._provider
    flattened = provider.calls[0]["user"]
    assert flattened.index("Je veux un rédacteur") < flattened.index("Quel type de contenu ?")
    assert flattened.index("Quel type de contenu ?") < flattened.index("Des articles de blog.")


# ------------------------------------------------------------------
# Fallback sans fichier agent-creator.md
# ------------------------------------------------------------------


async def test_prompt_manquant_echoue_au_lieu_de_degrader(tmp_path: Path) -> None:
    # Créer un agent sans le prompt de l'agent-creator produisait un agent
    # au prompt bancal, réutilisé ensuite à chaque run (ticket-051).
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    svc = AgentCreatorService(provider=_make_provider(_VALID_AGENT_JSON), prompts_dir=prompts_dir)

    with pytest.raises(MissingPromptError) as exc:
        await svc.create_agent([_user("Un rédacteur")])

    assert "agent-creator.md" in str(exc.value)
    assert "IDE_PROMPTS_DIR" in str(exc.value)


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
