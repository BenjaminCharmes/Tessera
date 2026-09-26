"""Regression tests — ticket-044 review, finding 1 (critical).

``AgentRunner`` resolves ``project_path`` into the SDK ``cwd``. If the router
never passes it, the SDK inherits the backend process's working directory and
writes into the wrong project (and loads the wrong CLAUDE.md via
``setting_sources=["project"]``). These tests pin that ``_make_runner`` wires
``project_path`` to this project's workspace directory.
"""
from pathlib import Path

import pytest

from tessera.config import settings
from tessera.routers.agents import _make_agent_creator, _make_project_creator, _make_runner
from tessera.services.providers.agent_sdk import ClaudeAgentSDKProvider


@pytest.fixture(autouse=True)
def _isolated_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(settings, "ide_workspace_dir", tmp_path)
    # Pin the provider so these tests are deterministic regardless of a
    # developer's local .env — ``LLM_PROVIDER=anthropic_api`` would make
    # ``runner._provider._allowed_tools`` raise AttributeError (ticket-044
    # merge-gate review, finding 4).
    monkeypatch.setattr(settings, "llm_provider", "agent_sdk")
    return tmp_path


def test_make_runner_sets_project_path_to_workspace_project_dir(tmp_path: Path) -> None:
    runner = _make_runner("mon-projet")
    assert runner._project_path == tmp_path / "mon-projet"


def test_make_runner_project_path_varies_with_project_id(tmp_path: Path) -> None:
    runner_a = _make_runner("projet-a")
    runner_b = _make_runner("projet-b")
    assert runner_a._project_path == tmp_path / "projet-a"
    assert runner_b._project_path == tmp_path / "projet-b"


def test_make_runner_garde_le_jeu_d_outils_complet() -> None:
    runner = _make_runner("mon-projet")
    assert runner._provider._allowed_tools == [
        "Read", "Write", "Edit", "Bash", "Glob", "Grep",
    ]


def test_make_agent_creator_n_a_aucun_outil() -> None:
    """Regression — ticket-044 review, finding 4: agent_creator is pure
    text-in/JSON-out and has no use for file/shell tools."""
    creator = _make_agent_creator()
    assert creator._provider._allowed_tools == []


def test_make_project_creator_n_a_aucun_outil() -> None:
    """Regression — ticket-044 merge-gate finding 2 (critical):
    ProjectCreatorService is pure text-in/JSON-out (it writes files itself
    in Python via ProjectLoader, never through an SDK tool), and nothing
    wires it a resolved ``cwd``. Combined with the full toolset and
    ``permission_mode="acceptEdits"``, that would auto-approve
    Write/Edit/Bash rooted in the backend process's own cwd."""
    creator = _make_project_creator()
    assert creator._provider._allowed_tools == []


def test_make_runner_donne_au_reviewer_des_outils_en_lecture_seule() -> None:
    # Un filtre écrit dans `AgentRunner` mais jamais branché par le routeur
    # ne filtre rien : c'est ici que le produit construit ses runners.
    runner = _make_runner("mon-projet")
    assert runner._provider_pour("reviewer")._allowed_tools == ["Read", "Glob", "Grep"]
    # Depuis ticket-188 chaque rôle a son provider : le codeur n'est plus
    # l'instance commune, mais il garde le jeu d'outils complet.
    assert runner._provider_pour("codeur")._allowed_tools == ClaudeAgentSDKProvider.ALLOWED_TOOLS
