"""Un ticket repris sur une branche déjà travaillée — ticket-497."""
from pathlib import Path

from tessera.models.agent import AgentRole
from tessera.services.orchestrator import EventType, Orchestrator, OrchestratorEvent
from tessera.services.test_runner import TestResult
from tests.test_orchestrator import _FakeGit, _make_orchestrator, _RecordingRunner

_VERT = TestResult(passed=True, total=5, failed=0, output_summary="5 passed in 0.5s")
_ROUGE = TestResult(
    passed=False,
    total=5,
    failed=1,
    output_summary="1 failed, 4 passed in 0.5s",
    errors=["FAILED tests/test_x.py::test_x"],
)
_EXPIRE = TestResult(
    passed=False, total=0, failed=0, output_summary="Timeout après 60s", expiree=True
)


class _GitReprise(_FakeGit):
    """Fake git whose branch carries ``commits_repris`` earlier commits."""

    def __init__(self, commits_repris: int) -> None:
        super().__init__()
        self.commits_repris = commits_repris


class _FakeTestRunner:
    """Rend les résultats dans l'ordre, le dernier se répétant."""

    def __init__(self, *results: TestResult) -> None:
        self._results = list(results)
        self.calls = 0

    async def run_tests(
        self,
        project_path: Path,
        test_command: str | None = None,
        en_attente: object = None,
    ) -> TestResult:
        self.calls += 1
        if len(self._results) > 1:
            return self._results.pop(0)
        return self._results[0]


def _roles(runner: _RecordingRunner) -> list[AgentRole]:
    return [c["role"] for c in runner.calls]  # type: ignore[misc]


def _orchestrateur(
    tmp_path: Path,
    git: _FakeGit,
    test_runner: _FakeTestRunner | None,
) -> tuple[Orchestrator, _RecordingRunner]:
    runner = _RecordingRunner()
    orchestrator = _make_orchestrator(
        tmp_path, runner=runner, git_workspace=git, project_path=tmp_path  # type: ignore[arg-type]
    )
    orchestrator._test_runner = test_runner  # type: ignore[assignment]
    return orchestrator, runner


async def _lancer(
    orchestrator: Orchestrator,
) -> list[OrchestratorEvent]:
    events: list[OrchestratorEvent] = []

    async def _collect(event: OrchestratorEvent) -> None:
        events.append(event)

    await orchestrator.run_pipeline("projet", "ticket-001", _collect)
    return events


def _reprises(events: list[OrchestratorEvent]) -> list[OrchestratorEvent]:
    return [e for e in events if e.type == EventType.RUN_RESUMED_FROM_EXISTING_WORK]


async def test_resumed_branch_with_green_tests_skips_the_coder(tmp_path: Path) -> None:
    tests = _FakeTestRunner(_VERT)
    orchestrator, runner = _orchestrateur(tmp_path, _GitReprise(3), tests)

    await _lancer(orchestrator)

    assert _roles(runner) == [AgentRole.reviewer]
    assert tests.calls == 1


async def test_resumed_branch_with_red_tests_calls_the_coder_with_the_result(
    tmp_path: Path,
) -> None:
    tests = _FakeTestRunner(_ROUGE, _VERT)
    orchestrator, runner = _orchestrateur(tmp_path, _GitReprise(2), tests)

    await _lancer(orchestrator)

    assert _roles(runner)[0] == AgentRole.codeur
    contexte = str(runner.calls[0]["project_context"])
    assert "1 failed, 4 passed" in contexte
    assert "FAILED tests/test_x.py::test_x" in contexte


async def test_resumed_branch_whose_tests_time_out_twice_goes_to_the_coder(
    tmp_path: Path,
) -> None:
    tests = _FakeTestRunner(_EXPIRE, _EXPIRE, _VERT)
    orchestrator, runner = _orchestrateur(tmp_path, _GitReprise(2), tests)

    events = await _lancer(orchestrator)

    assert _roles(runner)[0] == AgentRole.codeur
    assert _reprises(events)[0].data["verdict"] == "red"


async def test_fresh_branch_calls_the_coder_first(tmp_path: Path) -> None:
    tests = _FakeTestRunner(_VERT)
    orchestrator, runner = _orchestrateur(tmp_path, _GitReprise(0), tests)

    events = await _lancer(orchestrator)

    assert _roles(runner)[0] == AgentRole.codeur
    assert tests.calls == 1, "les tests ne tournent qu'après le codeur"
    assert _reprises(events) == []


async def test_workspace_without_resume_count_calls_the_coder_first(
    tmp_path: Path,
) -> None:
    orchestrator, runner = _orchestrateur(tmp_path, _FakeGit(), _FakeTestRunner(_VERT))

    await _lancer(orchestrator)

    assert _roles(runner)[0] == AgentRole.codeur


async def test_resumed_branch_without_tester_calls_the_coder_first(
    tmp_path: Path,
) -> None:
    orchestrator, runner = _orchestrateur(tmp_path, _GitReprise(4), None)

    events = await _lancer(orchestrator)

    assert _roles(runner)[0] == AgentRole.codeur
    assert _reprises(events) == []


async def test_resumed_event_carries_commits_and_green_verdict(tmp_path: Path) -> None:
    orchestrator, _ = _orchestrateur(tmp_path, _GitReprise(3), _FakeTestRunner(_VERT))

    events = await _lancer(orchestrator)

    (event,) = _reprises(events)
    assert event.ticket_id == "ticket-001"
    assert event.data == {"commits": 3, "verdict": "green"}
    journal = (tmp_path / "memory" / "pipeline-log.md").read_text(encoding="utf-8")
    assert "branche reprise (3 commit(s)) — tests green, codeur sauté" in journal


async def test_resumed_event_carries_red_verdict(tmp_path: Path) -> None:
    orchestrator, _ = _orchestrateur(
        tmp_path, _GitReprise(1), _FakeTestRunner(_ROUGE, _VERT)
    )

    events = await _lancer(orchestrator)

    (event,) = _reprises(events)
    assert event.data == {"commits": 1, "verdict": "red"}
    journal = (tmp_path / "memory" / "pipeline-log.md").read_text(encoding="utf-8")
    assert "tests red, codeur en premier" in journal


async def test_skipped_coder_still_reaches_the_reviewer_with_the_real_diff(
    tmp_path: Path,
) -> None:
    orchestrator, runner = _orchestrateur(tmp_path, _GitReprise(1), _FakeTestRunner(_VERT))

    await _lancer(orchestrator)

    contexte = str(runner.calls[0]["project_context"])
    assert "SECRET = 'hunter2'" in contexte
    assert "5 passed in 0.5s" in contexte


async def test_resumed_branch_whose_test_launcher_fails_is_not_taken_for_green(
    tmp_path: Path,
) -> None:
    class _Casse:
        async def run_tests(self, *args: object, **kwargs: object) -> TestResult:
            raise RuntimeError("lanceur en panne")

    orchestrator, runner = _orchestrateur(tmp_path, _GitReprise(2), _Casse())  # type: ignore[arg-type]

    events = await _lancer(orchestrator)

    assert _roles(runner)[0] == AgentRole.codeur
    assert _reprises(events)[0].data["verdict"] == "red"
    contexte = str(runner.calls[0]["project_context"])
    assert "n'ont pas pu aller au bout" in contexte
