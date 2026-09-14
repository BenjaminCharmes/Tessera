"""Regression tests — ticket-044 review, finding 1 (critical).

``_build_orchestrator`` already computes ``project_path`` and forwards it to
the ``Orchestrator``. But the ``AgentRunner`` it builds a few lines earlier
never receives it, so the SDK falls back to the backend process's cwd instead
of the project's workspace directory. This pins that the runner used by the
orchestrator gets the same ``project_path``.
"""
from pathlib import Path

import pytest

from vibe_ide.config import settings
from vibe_ide.routers.orchestrator import _build_orchestrator


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


def _make_project_with_doc_updater(workspace: Path, project_id: str) -> None:
    project_dir = workspace / project_id
    project_dir.mkdir(parents=True)
    (project_dir / "CLAUDE.md").write_text("# Projet de test\n", encoding="utf-8")
    (project_dir / "memory").mkdir()
    (project_dir / "agents.json").write_text(
        '{"agents": [], "pipeline": {"doc_updater_enabled": true}}',
        encoding="utf-8",
    )


async def test_build_orchestrator_doc_updater_sans_outils(tmp_path: Path) -> None:
    """Regression — ticket-044 merge-gate finding 2 (critical): doc_updater
    is pure text-in/JSON-out (it writes files itself in Python via
    ``_write_files``, never through an SDK tool). Wiring it to the full-tool
    provider combines auto-approved Write/Edit/Bash with ``cwd=None``
    (nothing calls ``DocUpdaterService`` with a resolved cwd), which would
    let the model write anywhere under the backend process's own cwd."""
    _make_project_with_doc_updater(tmp_path, "mon-projet")

    orchestrator = await _build_orchestrator("mon-projet")

    assert orchestrator._doc_updater is not None
    assert orchestrator._doc_updater._provider._allowed_tools == []
    # The coder/reviewer runner keeps the full toolset.
    assert orchestrator._runner._provider._allowed_tools == [
        "Read", "Write", "Edit", "Bash", "Glob", "Grep",
    ]
