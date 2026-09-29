"""Regression tests — ticket-044 review, finding 1 (critical).

``_build_orchestrator`` already computes ``project_path`` and forwards it to
the ``Orchestrator``. But the ``AgentRunner`` it builds a few lines earlier
never receives it, so the SDK falls back to the backend process's cwd instead
of the project's workspace directory. This pins that the runner used by the
orchestrator gets the same ``project_path``.
"""
from pathlib import Path

import pytest

from tessera.config import settings
from tessera.routers.orchestrator import _build_orchestrator, _build_project_context


@pytest.fixture(autouse=True)
def _isolated_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(settings, "ide_workspace_dir", tmp_path)
    # Pin the provider so these tests are deterministic regardless of a
    # developer's local .env — ``LLM_PROVIDER=anthropic_api`` would make
    # ``..._provider._allowed_tools`` raise AttributeError (ticket-044
    # merge-gate review, finding 4).
    monkeypatch.setattr(settings, "llm_provider", "agent_sdk")
    return tmp_path


def _make_minimal_project(workspace: Path, project_id: str) -> None:
    project_dir = workspace / project_id
    project_dir.mkdir(parents=True)
    (project_dir / "CLAUDE.md").write_text("# Projet de test\n", encoding="utf-8")
    (project_dir / "memory").mkdir()


async def test_build_orchestrator_runner_receives_project_path(tmp_path: Path) -> None:
    _make_minimal_project(tmp_path, "mon-projet")

    orchestrator = await _build_orchestrator("mon-projet")

    assert orchestrator._runner._project_path == tmp_path / "mon-projet"


def _make_project_with_pipeline(workspace: Path, project_id: str) -> None:
    project_dir = workspace / project_id
    project_dir.mkdir(parents=True)
    (project_dir / "CLAUDE.md").write_text("# Projet de test\n", encoding="utf-8")
    (project_dir / "memory").mkdir()
    (project_dir / "agents.json").write_text(
        '{"agents": [], "pipeline": {"securite_enabled": true, "validateur_enabled": true}}',
        encoding="utf-8",
    )


async def test_build_orchestrator_validator_et_security_auditor_sans_outils(
    tmp_path: Path,
) -> None:
    """Regression — ticket-044 review, finding 4: validator and
    security_auditor are pure text-in/JSON-out and must not receive the
    coder/reviewer runner's full file/shell toolset."""
    _make_project_with_pipeline(tmp_path, "mon-projet")

    orchestrator = await _build_orchestrator("mon-projet")

    assert orchestrator._validator is not None
    assert orchestrator._security_auditor is not None
    assert orchestrator._validator._provider._allowed_tools == []
    assert orchestrator._security_auditor._provider._allowed_tools == []
    # The coder/reviewer runner keeps the full toolset.
    assert orchestrator._runner._provider._allowed_tools == [
        "Read", "Write", "Edit", "Bash", "Glob", "Grep",
    ]


async def test_build_orchestrator_passe_le_dossier_et_le_delai_des_tests(
    tmp_path: Path,
) -> None:
    # Ticket-241 : sans eux, le testeur d'ide-core lance ses tests depuis un
    # dossier qui n'en contient pas, et coupe la suite à 120 s.
    project_dir = tmp_path / "mon-projet"
    project_dir.mkdir(parents=True)
    (project_dir / "CLAUDE.md").write_text("# Projet de test\n", encoding="utf-8")
    (project_dir / "agents.json").write_text(
        '{"agents": [], "pipeline": {"testeur_enabled": true, "test_command": "pytest",'
        ' "test_cwd": "backend", "test_timeout_s": 600}}',
        encoding="utf-8",
    )

    orchestrator = await _build_orchestrator("mon-projet")

    assert orchestrator._test_runner is not None
    assert orchestrator._test_runner._cwd == "backend"
    assert orchestrator._test_runner._timeout == 600


def _make_project_with_claude_md_marker(workspace: Path, project_id: str) -> None:
    project_dir = workspace / project_id
    project_dir.mkdir(parents=True)
    (project_dir / "CLAUDE.md").write_text(
        "MARQUEUR_CLAUDE_MD_UNIQUE\n", encoding="utf-8"
    )


async def test_project_context_ne_duplique_pas_claude_md_sur_le_provider_sdk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With the SDK provider, CLAUDE.md is read via cwd — do not re-inject it."""
    monkeypatch.setattr(settings, "llm_provider", "agent_sdk")
    monkeypatch.setattr(settings, "ide_workspace_dir", tmp_path)
    _make_project_with_claude_md_marker(tmp_path, "mon-projet")

    context = await _build_project_context("mon-projet")

    assert "MARQUEUR_CLAUDE_MD_UNIQUE" not in context


async def test_project_context_conserve_claude_md_sur_le_provider_api(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """On the Messages API there is no cwd: the injection is still needed."""
    monkeypatch.setattr(settings, "llm_provider", "anthropic_api")
    monkeypatch.setattr(settings, "ide_workspace_dir", tmp_path)
    _make_project_with_claude_md_marker(tmp_path, "mon-projet")

    context = await _build_project_context("mon-projet")

    assert "MARQUEUR_CLAUDE_MD_UNIQUE" in context
