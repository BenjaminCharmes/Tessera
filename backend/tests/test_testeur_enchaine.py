"""The testeur runs every step of an `&&` chain — ticket-337.

Lancée sans shell, `a && b` ne faisait tourner que `a` quand `a` est un
exécutable natif : `&&` et la suite devenaient ses arguments, et le testeur
annonçait vert ce qu'il n'avait pas lancé. Avec `npm` en tête, `npm.cmd`
passait par cmd.exe, qui enchaînait — par chance, et seulement sous Windows.
"""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from tessera.services.test_runner import TestResult, TestRunnerService

PY = f'"{sys.executable}" -c'


def _sortie(code: int) -> str:
    return f'{PY} "import sys; sys.exit({code})"'


async def test_a_failing_later_step_fails_the_run(tmp_path: Path) -> None:
    result = await TestRunnerService().run_tests(
        tmp_path, test_command=f"{_sortie(0)} && {_sortie(4)}"
    )

    assert result.passed is False
    assert result.demarree is True
    assert [e.code for e in result.etapes] == [0, 4]


async def test_the_chain_stops_at_the_first_failure(tmp_path: Path) -> None:
    result = await TestRunnerService().run_tests(
        tmp_path, test_command=f"{_sortie(2)} && {_sortie(0)}"
    )

    assert result.passed is False
    assert [e.code for e in result.etapes] == [2]


async def test_every_step_green_is_green_and_each_step_is_recorded(tmp_path: Path) -> None:
    result = await TestRunnerService().run_tests(
        tmp_path, test_command=f"{_sortie(0)} && {_sortie(0)}"
    )

    assert result.passed is True
    assert len(result.etapes) == 2
    assert all(e.code == 0 for e in result.etapes)
    assert "sys.exit(0)" in result.etapes[1].commande


async def test_an_unsupported_operator_does_not_start(tmp_path: Path) -> None:
    result = await TestRunnerService().run_tests(
        tmp_path, test_command=f"{_sortie(0)} | {_sortie(0)}"
    )

    assert result.passed is False
    assert result.demarree is False
    assert "|" in result.output_summary


async def test_failure_details_in_coder_context(tmp_path: Path) -> None:
    """Ticket-393 : failure_details from the test result reaches the coder's context.

    The pipeline stage ``run_tests`` must include ``failure_details`` in
    ``run.test_context``, which is the piece appended to the coder's prompt on
    the next turn.
    """
    from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
    from tessera.services import pipeline_stages
    from tessera.services.pipeline_run import PipelineRun

    failure_detail = "FAILED tests/test_foo.py::test_bar - assert [5, 6] == [5]\n\nE   AssertionError: assert [5, 6] == [5]"
    mock_test_result = TestResult(
        passed=False,
        total=5,
        failed=1,
        output_summary="1 failed, 4 passed in 1.23s",
        errors=["FAILED tests/test_foo.py::test_bar"],
        failure_details=failure_detail,
    )

    mock_runner = MagicMock()
    mock_runner.run_tests = AsyncMock(return_value=mock_test_result)

    orch = MagicMock()
    orch._test_runner = mock_runner
    orch._project_path = tmp_path
    orch._test_command = None
    orch._log = MagicMock()

    ticket = Ticket(
        id="ticket-000",
        title="test ticket",
        type=TicketType.feat,
        status=TicketStatus.in_progress,
        priority=TicketPriority.medium,
        agent="codeur",
    )
    run = PipelineRun(
        project_id="proj",
        ticket=ticket,
        on_event=AsyncMock(),
    )

    await pipeline_stages.run_tests(orch, run)

    assert failure_detail in run.test_context
    assert "Détail des échecs:" in run.test_context
