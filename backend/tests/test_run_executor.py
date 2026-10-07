"""Pipeline log is updated when the queue dies — ticket-377.

When `executer` catches an unhandled exception (e.g. a crash inside
`run_pipeline`), it must write a `file interrompue` line to the project's
`memory/pipeline-log.md` so the user can see from the IDE that the queue
stopped, instead of waiting forever.

The orchestrator already writes these lines for the cases it controls
(non-approved ticket, budget exhausted, stop requested).  This test covers
the uncontrolled case: an exception that bypasses the orchestrator entirely.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tessera.config import settings
from tessera.services.event_hub import EventHub
from tessera.services.run_executor import executer
from tessera.services.run_registry import RunActif, RunRegistry
from tessera.services.database import init_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _OrchestratorQuiExplose:
    """Minimal orchestrator stub that always raises on run_pipeline."""

    def __init__(self, message: str = "crash inattendu") -> None:
        self._message = message

    async def run_pipeline(self, *args: Any, **kwargs: Any) -> Any:
        raise RuntimeError(self._message)

    async def run_queue(self, *args: Any, **kwargs: Any) -> Any:
        raise RuntimeError(self._message)

    async def run_autonomous(self, *args: Any, **kwargs: Any) -> Any:
        raise RuntimeError(self._message)


def _make_run(registry: RunRegistry, project_id: str = "mon-projet") -> RunActif:
    return registry.ouvrir(project_id, ticket_id="ticket-901", mode="single")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_exception_pipeline_ecrit_dans_pipeline_log(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An exception in run_pipeline writes a 'file interrompue' line to pipeline-log.md."""
    # Workspace fictif
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    project_dir = workspace / "mon-projet"
    project_dir.mkdir()

    db_path = tmp_path / "tessera.db"
    await init_db(db_path)

    monkeypatch.setattr(settings, "ide_workspace_dir", workspace)
    monkeypatch.setattr(settings, "ide_db_path", db_path)

    hub = EventHub()
    registry = RunRegistry()
    run = _make_run(registry)
    orchestrator = _OrchestratorQuiExplose("panne simulée pour test-377")

    await executer(run, orchestrator, hub, registry)

    log_path = project_dir / "memory" / "pipeline-log.md"
    assert log_path.exists(), "pipeline-log.md doit avoir été créé"
    content = log_path.read_text(encoding="utf-8")
    assert "file interrompue" in content, (
        f"'file interrompue' absent du pipeline-log.md : {content!r}"
    )
    assert "panne simulée pour test-377" in content, (
        f"le message d'erreur est absent du pipeline-log.md : {content!r}"
    )


async def test_exception_pipeline_mentionne_le_projet(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The 'file interrompue' line in pipeline-log.md includes the project id."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    project_dir = workspace / "autre-projet"
    project_dir.mkdir()

    db_path = tmp_path / "tessera.db"
    await init_db(db_path)

    monkeypatch.setattr(settings, "ide_workspace_dir", workspace)
    monkeypatch.setattr(settings, "ide_db_path", db_path)

    hub = EventHub()
    registry = RunRegistry()
    run = registry.ouvrir("autre-projet", ticket_id="ticket-001", mode="single")
    orchestrator = _OrchestratorQuiExplose("erreur quelconque")

    await executer(run, orchestrator, hub, registry)

    log_path = project_dir / "memory" / "pipeline-log.md"
    assert log_path.exists(), "pipeline-log.md doit avoir été créé"
    content = log_path.read_text(encoding="utf-8")
    assert "[autre-projet]" in content, (
        f"le nom du projet doit figurer dans le pipeline-log.md : {content!r}"
    )
