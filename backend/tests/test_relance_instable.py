"""A timed-out test file outside the diff is run again once, alone (ticket-971)."""
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from tessera.services.git_workspace import GitWorkspaceError
from tessera.services.pipeline import pipeline_testeur
from tessera.services.pipeline.pipeline_run import PipelineRun
from tessera.services.verification.relance_instable import fichiers_a_relancer, touche_le_diff
from tessera.services.verification.resultat_de_test import TestResult
from tessera.services.verification.test_runner import TestRunnerService

VITEST_TIMEOUT = """
 FAIL  src/play-screen.test.tsx > PlayScreen > shows the board
Error: Test timed out in 5000ms.
 Test Files  1 failed (1)
"""
VITEST_FIND_BY = """
 FAIL  src/StatsView/RecentRunsCard.test.tsx > RecentRunsCard > filters
TestingLibraryElementError: Unable to find an element with the text: zzz
"""
VITEST_ASSERT = """
 FAIL  src/play-screen.test.tsx > PlayScreen > shows the board
AssertionError: expected 1 to be 2
"""
PYTEST_TIMEOUT = """
=========================== short test summary info ===========================
FAILED tests/test_slow.py::test_wait - Failed: Timeout >5.0s
"""
PYTEST_ASSERT = """
FAILED tests/test_slow.py::test_wait - assert 1 == 2
"""
VERT = "Tests  3 passed (3)"


class _Executeur:
    """Replaces `_executer`: first call is the failing step, next ones the retry."""

    def __init__(self, premiere: str, relance: str, code_relance: int) -> None:
        self.sorties = [(1, premiere), (code_relance, relance)]
        self.args: list[list[str]] = []

    async def __call__(self, args: list[str], *_rest: object) -> tuple[int, str]:
        self.args.append(args)
        return self.sorties[min(len(self.args) - 1, 1)]


def _projet(tmp_path: Path, fichier: str) -> Path:
    cible = tmp_path / "frontend" / fichier
    cible.parent.mkdir(parents=True, exist_ok=True)
    cible.write_text("", encoding="utf-8")
    return tmp_path


async def _lancer(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, premiere: str, relance: str,
    code_relance: int, diff: list[str],
) -> tuple[TestResult, _Executeur]:
    executeur = _Executeur(premiere, relance, code_relance)
    monkeypatch.setattr(TestRunnerService, "_executer", executeur)
    for fichier in ("src/play-screen.test.tsx", "src/StatsView/RecentRunsCard.test.tsx", "tests/test_slow.py"):
        _projet(tmp_path, fichier)
    (tmp_path / "frontend" / "tests").mkdir(exist_ok=True)
    (tmp_path / "frontend" / "tests" / "test_slow.py").write_text("", encoding="utf-8")
    runner = TestRunnerService()
    result = await runner.run_tests(tmp_path, test_command="echo x", fichiers_du_diff=diff)
    return result, executeur


async def test_vitest_timeout_outside_diff_is_rerun_alone_and_green(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    result, executeur = await _lancer(monkeypatch, tmp_path, VITEST_TIMEOUT, VERT, 0, ["backend/x.py"])
    assert result.passed
    assert executeur.args[1] == ["npx", "vitest", "run", "src/play-screen.test.tsx"]
    assert result.instables_relances == ["src/play-screen.test.tsx"]


async def test_testing_library_find_by_expiry_is_rerun(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    result, executeur = await _lancer(monkeypatch, tmp_path, VITEST_FIND_BY, VERT, 0, [])
    assert result.passed
    assert len(executeur.args) == 2


async def test_red_rerun_keeps_step_red_with_both_outputs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    result, _ = await _lancer(monkeypatch, tmp_path, VITEST_TIMEOUT, "Test timed out again", 1, [])
    assert not result.passed
    assert "Test timed out in 5000ms" in result.failure_details
    assert "Test timed out again" in result.failure_details
    assert result.instables_relances == []


async def test_file_in_diff_is_not_rerun(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    result, executeur = await _lancer(
        monkeypatch, tmp_path, VITEST_TIMEOUT, VERT, 0, ["frontend/src/play-screen.test.tsx"]
    )
    assert not result.passed
    assert len(executeur.args) == 1


async def test_assertion_failure_is_not_rerun(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    result, executeur = await _lancer(monkeypatch, tmp_path, VITEST_ASSERT, VERT, 0, [])
    assert not result.passed
    assert len(executeur.args) == 1


async def test_pytest_timeout_is_rerun_alone(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    result, executeur = await _lancer(monkeypatch, tmp_path, PYTEST_TIMEOUT, "1 passed in 0.1s", 0, [])
    assert result.passed
    assert executeur.args[1][-1] == "tests/test_slow.py"


async def test_unknown_diff_never_reruns(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    executeur = _Executeur(VITEST_TIMEOUT, VERT, 0)
    monkeypatch.setattr(TestRunnerService, "_executer", executeur)
    result = await TestRunnerService().run_tests(tmp_path, test_command="echo x")
    assert not result.passed
    assert len(executeur.args) == 1


def test_fichiers_a_relancer_reads_each_kind() -> None:
    assert fichiers_a_relancer(VITEST_TIMEOUT, []) == {"vitest": ["src/play-screen.test.tsx"]}
    assert fichiers_a_relancer(PYTEST_TIMEOUT, []) == {"pytest": ["tests/test_slow.py"]}
    assert fichiers_a_relancer(PYTEST_ASSERT, []) == {}
    assert fichiers_a_relancer(VITEST_TIMEOUT + PYTEST_ASSERT, []) == {}


def test_touche_le_diff_matches_test_file_and_sibling_code() -> None:
    fichier = "src/StatsView/RecentRunsCard.test.tsx"
    assert touche_le_diff(fichier, ["frontend/src/StatsView/RecentRunsCard.tsx"])
    assert touche_le_diff(fichier, ["frontend/src/StatsView/RecentRunsCard.test.tsx"])
    assert not touche_le_diff(fichier, ["frontend/src/StatsView/Other.tsx", "backend/a.py"])


def _orch_du_testeur(tmp_path: Path, workspace: object) -> tuple[MagicMock, PipelineRun]:
    from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType

    orch = MagicMock()
    orch._test_runner.run_tests = AsyncMock(
        return_value=TestResult(passed=True, total=1, failed=0, output_summary="1 passed")
    )
    orch._project_path = tmp_path
    orch._test_command = None
    orch._git_workspace = workspace
    ticket = Ticket(
        id="ticket-000", title="t", type=TicketType.feat, status=TicketStatus.in_progress,
        priority=TicketPriority.medium, agent="codeur",
    )
    return orch, PipelineRun(project_id="p", ticket=ticket, on_event=AsyncMock())


async def test_stage_passes_none_when_the_diff_cannot_be_read(tmp_path: Path) -> None:
    for diff_depuis_base in (AsyncMock(side_effect=GitWorkspaceError("boom")), None):
        workspace = MagicMock(spec=[] if diff_depuis_base is None else ["diff_depuis_base"])
        if diff_depuis_base is not None:
            workspace.diff_depuis_base = diff_depuis_base
        orch, run = _orch_du_testeur(tmp_path, workspace)
        await pipeline_testeur.run_tests(orch, run)
        assert orch._test_runner.run_tests.call_args.kwargs["fichiers_du_diff"] is None


async def test_stage_passes_the_changed_paths_when_the_diff_is_read(tmp_path: Path) -> None:
    diff = "diff --git a/frontend/src/a.tsx b/frontend/src/a.tsx\n--- a/frontend/src/a.tsx\n+++ b/frontend/src/a.tsx\n@@ -1 +1 @@\n-x\n+y\n"
    workspace = MagicMock(spec=["diff_depuis_base"])
    workspace.diff_depuis_base = AsyncMock(return_value=diff)
    orch, run = _orch_du_testeur(tmp_path, workspace)
    await pipeline_testeur.run_tests(orch, run)
    assert orch._test_runner.run_tests.call_args.kwargs["fichiers_du_diff"] == ["frontend/src/a.tsx"]
