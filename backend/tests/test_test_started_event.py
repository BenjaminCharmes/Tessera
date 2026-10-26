"""The testeur announces its start — ticket-587.

Between `test_started` and `test_result` the testeur emits nothing for minutes:
the UI needs the start to tell a long suite from a frozen agent.
"""
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services import pipeline_stages
from tessera.services.pipeline_events import EventType, OrchestratorEvent
from tessera.services.pipeline_run import PipelineRun
from tessera.services.test_runner import TestResult


def _run(journal: list[str]) -> PipelineRun:
    async def on_event(ev: OrchestratorEvent) -> None:
        journal.append(ev.type.value)

    ticket = Ticket(
        id="ticket-000",
        title="test ticket",
        type=TicketType.feat,
        status=TicketStatus.in_progress,
        priority=TicketPriority.medium,
        agent="codeur",
    )
    return PipelineRun(project_id="proj", ticket=ticket, on_event=on_event)


def _orch(tmp_path: Path, journal: list[str]) -> MagicMock:
    async def run_tests(*_args: object, **_kwargs: object) -> TestResult:
        journal.append("runner")
        return TestResult(passed=True, total=1, failed=0, output_summary="1 passed")

    orch = MagicMock()
    orch._test_runner.run_tests = AsyncMock(side_effect=run_tests)
    orch._project_path = tmp_path
    orch._test_command = None
    return orch


async def test_test_started_is_emitted_before_the_suite_and_before_test_result(
    tmp_path: Path,
) -> None:
    journal: list[str] = []

    await pipeline_stages.run_tests(_orch(tmp_path, journal), _run(journal))

    assert journal == [EventType.TEST_STARTED.value, "runner", EventType.TEST_RESULT.value]


async def test_no_test_started_without_a_testeur(tmp_path: Path) -> None:
    journal: list[str] = []
    orch = _orch(tmp_path, journal)
    orch._test_runner = None

    await pipeline_stages.run_tests(orch, _run(journal))

    assert journal == []
