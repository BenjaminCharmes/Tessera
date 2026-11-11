import subprocess
from pathlib import Path

from tessera.services.git_workspace.chemins import (
    _ORCHESTRATOR_ARTIFACT_EXCLUDE_PATHSPECS,
    _is_orchestrator_artifact_path,
)
from tessera.services.projets.artifacts import apply_artifact_mode


def test_journal_archive_is_an_orchestrator_artifact() -> None:
    assert _is_orchestrator_artifact_path("memory/journal/pipeline-log-2026-09.md")
    assert ":(exclude)memory/journal/" in _ORCHESTRATOR_ARTIFACT_EXCLUDE_PATHSPECS


async def test_journal_archive_is_excluded_in_local_mode(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    await apply_artifact_mode(tmp_path, "local")
    res = subprocess.run(
        ["git", "check-ignore", "-q", "--", "memory/journal/x.md"], cwd=tmp_path
    )
    assert res.returncode == 0
