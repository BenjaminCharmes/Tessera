from pathlib import Path

import pytest

from tessera.services.agent_registry import (
    AgentInfo,
    AgentNotFoundError,
    AgentRegistryService,
)


def _registry(tmp_path: Path) -> AgentRegistryService:
    return AgentRegistryService(tmp_path / "prompts")


def _registry_with_prompt(tmp_path: Path, role: str, content: str) -> AgentRegistryService:
    prompts = tmp_path / "prompts"
    prompts.mkdir(parents=True)
    (prompts / f"{role}.md").write_text(content, encoding="utf-8")
    return AgentRegistryService(prompts)


# ------------------------------------------------------------------
# list_agents
# ------------------------------------------------------------------


def test_list_agents_returns_all_builtins(tmp_path: Path) -> None:
    reg = _registry(tmp_path)
    agents = reg.list_agents()
    roles = {a.role for a in agents}
    assert AgentRegistryService.BUILTIN_ROLES.issubset(roles)


def test_list_agents_marks_builtins_correctly(tmp_path: Path) -> None:
    reg = _registry(tmp_path)
    agents = {a.role: a for a in reg.list_agents()}
    assert agents["codeur"].is_builtin is True
    assert agents["reviewer"].is_builtin is True


def test_list_agents_includes_custom_from_prompts_dir(tmp_path: Path) -> None:
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "redacteur.md").write_text("Tu es rédacteur.", encoding="utf-8")
    reg = AgentRegistryService(prompts)

    agents = {a.role: a for a in reg.list_agents()}
    assert "redacteur" in agents
    assert agents["redacteur"].is_builtin is False
    assert agents["redacteur"].has_prompt is True


def test_list_agents_has_prompt_false_when_file_missing(tmp_path: Path) -> None:
    reg = _registry(tmp_path)
    agents = {a.role: a for a in reg.list_agents()}
    # prompts dir doesn't exist, so no built-in has a prompt file
    assert all(not a.has_prompt for a in agents.values() if a.is_builtin)


def test_list_agents_has_prompt_true_when_file_exists(tmp_path: Path) -> None:
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "codeur.md").write_text("Je code.", encoding="utf-8")
    reg = AgentRegistryService(prompts)

    agents = {a.role: a for a in reg.list_agents()}
    assert agents["codeur"].has_prompt is True
    assert agents["reviewer"].has_prompt is False


# ------------------------------------------------------------------
# get_prompt
# ------------------------------------------------------------------


def test_get_prompt_reads_file(tmp_path: Path) -> None:
    reg = _registry_with_prompt(tmp_path, "codeur", "Tu es le codeur.")
    assert reg.get_prompt("codeur") == "Tu es le codeur."


def test_get_prompt_raises_for_missing_agent(tmp_path: Path) -> None:
    reg = _registry(tmp_path)
    with pytest.raises(AgentNotFoundError, match="inconnu"):
        reg.get_prompt("inconnu")


def test_get_prompt_custom_agent(tmp_path: Path) -> None:
    reg = _registry_with_prompt(tmp_path, "traducteur", "Tu traduis.")
    assert reg.get_prompt("traducteur") == "Tu traduis."


# ------------------------------------------------------------------
# create_agent
# ------------------------------------------------------------------


def test_create_agent_writes_file(tmp_path: Path) -> None:
    reg = _registry(tmp_path)
    reg.create_agent("traducteur", "Je traduis.")

    prompt_file = tmp_path / "prompts" / "traducteur.md"
    assert prompt_file.exists()
    assert prompt_file.read_text(encoding="utf-8") == "Je traduis."


def test_create_agent_creates_prompts_dir_if_missing(tmp_path: Path) -> None:
    reg = _registry(tmp_path)
    reg.create_agent("analyseur", "J'analyse.")
    assert (tmp_path / "prompts" / "analyseur.md").exists()


def test_create_agent_overwrites_existing(tmp_path: Path) -> None:
    reg = _registry_with_prompt(tmp_path, "codeur", "v1")
    reg.create_agent("codeur", "v2")
    assert reg.get_prompt("codeur") == "v2"


def test_create_agent_rejects_invalid_name_uppercase(tmp_path: Path) -> None:
    reg = _registry(tmp_path)
    with pytest.raises(ValueError, match="invalide"):
        reg.create_agent("Codeur", "prompt")


def test_create_agent_rejects_invalid_name_starts_with_digit(tmp_path: Path) -> None:
    reg = _registry(tmp_path)
    with pytest.raises(ValueError, match="invalide"):
        reg.create_agent("1codeur", "prompt")


def test_create_agent_rejects_traversal_attempt(tmp_path: Path) -> None:
    reg = _registry(tmp_path)
    with pytest.raises(ValueError, match="invalide"):
        reg.create_agent("../evil", "malicious content")


def test_create_agent_accepts_hyphenated_name(tmp_path: Path) -> None:
    reg = _registry(tmp_path)
    reg.create_agent("mon-agent", "prompt")
    assert (tmp_path / "prompts" / "mon-agent.md").exists()


def test_create_agent_accepts_alphanumeric_name(tmp_path: Path) -> None:
    reg = _registry(tmp_path)
    reg.create_agent("agent42", "prompt")
    assert (tmp_path / "prompts" / "agent42.md").exists()


# ------------------------------------------------------------------
# delete_agent
# ------------------------------------------------------------------


def test_delete_agent_removes_file(tmp_path: Path) -> None:
    reg = _registry_with_prompt(tmp_path, "traducteur", "prompt")
    reg.delete_agent("traducteur")
    assert not (tmp_path / "prompts" / "traducteur.md").exists()


def test_delete_agent_refuses_builtin(tmp_path: Path) -> None:
    reg = _registry_with_prompt(tmp_path, "codeur", "prompt")
    with pytest.raises(ValueError, match="built-in"):
        reg.delete_agent("codeur")


def test_delete_agent_raises_for_missing(tmp_path: Path) -> None:
    reg = _registry(tmp_path)
    with pytest.raises(AgentNotFoundError):
        reg.delete_agent("fantome")


# ------------------------------------------------------------------
# is_builtin
# ------------------------------------------------------------------


def test_is_builtin_returns_true_for_known_builtins(tmp_path: Path) -> None:
    reg = _registry(tmp_path)
    for role in AgentRegistryService.BUILTIN_ROLES:
        assert reg.is_builtin(role) is True


def test_is_builtin_returns_false_for_custom(tmp_path: Path) -> None:
    reg = _registry(tmp_path)
    assert reg.is_builtin("redacteur") is False
    assert reg.is_builtin("mon-agent") is False
