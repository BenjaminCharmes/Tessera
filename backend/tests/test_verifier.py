"""Tests for scripts/verifier.py (tickets 304, 351).

The script runs two chains in parallel — backend (pytest → mypy) and frontend
(tsc → eslint → vitest) — each stopping at its first failure. Subprocess calls
are replaced by stubs so no real tool is invoked during the test suite.
"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add scripts/ to path so verifier.py can be imported as a regular module.
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from verifier import (  # noqa: E402
    BACKEND_STEPS,
    FRONTEND_STEPS,
    STEPS,
    Step,
    _run_chain,
    run_parallel,
    run_steps,
)

_FAKE_BACKEND = Path("/fake/backend")
_FAKE_FRONTEND = Path("/fake/frontend")

_PATCH = "verifier.subprocess.run"


def _result(returncode: int, stdout: str = "", stderr: str = "") -> MagicMock:
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = stderr
    return m


def _make_steps(*names: str) -> list[Step]:
    """Build minimal Step stubs for the given names."""
    cmds: dict[str, tuple[list[str], Path]] = {
        "pytest": (["python", "-m", "pytest"], _FAKE_BACKEND),
        "mypy": (["python", "-m", "mypy", "src/"], _FAKE_BACKEND),
        "tsc": (["npx", "tsc", "-b"], _FAKE_FRONTEND),
        "eslint": (["npx", "eslint", "."], _FAKE_FRONTEND),
        "vitest": (["npx", "vitest", "run"], _FAKE_FRONTEND),
    }
    return [Step(n, *cmds[n]) for n in names]


# ---------------------------------------------------------------------------
# Order and stop-on-failure (run_steps — backward compat)
# ---------------------------------------------------------------------------

def test_stops_at_first_failure() -> None:
    """Only the steps up to and including the failing one are executed."""
    steps = _make_steps("pytest", "mypy", "tsc")
    side_effects = [_result(0), _result(1, "mypy found errors"), _result(0)]
    with patch(_PATCH, side_effect=side_effects) as mock_run:
        run_steps(steps)
    assert mock_run.call_count == 2


def test_runs_all_steps_when_all_pass() -> None:
    """All steps are executed when none fails."""
    steps = _make_steps("pytest", "mypy", "tsc")
    with patch(_PATCH, return_value=_result(0)) as mock_run:
        run_steps(steps)
    assert mock_run.call_count == 3


def test_steps_called_in_declared_order() -> None:
    """Commands are issued in the order the steps are declared."""
    steps = _make_steps("pytest", "mypy")
    calls: list[list[str]] = []

    def capture(cmd: list[str], **_: object) -> MagicMock:
        calls.append(list(cmd))
        return _result(0)

    with patch(_PATCH, side_effect=capture):
        run_steps(steps)

    assert calls[0] == ["python", "-m", "pytest"]
    assert calls[1] == ["python", "-m", "mypy", "src/"]


# ---------------------------------------------------------------------------
# Output format on failure
# ---------------------------------------------------------------------------

def test_failure_output_starts_with_step_name(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """stderr begins with '<step_name> :' so the codeur sees which tool failed."""
    steps = _make_steps("mypy")
    with patch(_PATCH, return_value=_result(1, stdout="type error", stderr="")):
        run_steps(steps)
    captured = capsys.readouterr()
    assert captured.err.startswith("mypy :")


def test_failure_output_includes_tool_output(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The tool's stdout and stderr appear after the step name."""
    steps = _make_steps("eslint")
    with patch(_PATCH, return_value=_result(1, stdout="", stderr="no-undef error")):
        run_steps(steps)
    captured = capsys.readouterr()
    assert "no-undef error" in captured.err


def test_no_output_when_all_pass(capsys: pytest.CaptureFixture[str]) -> None:
    """No error output is written when every step succeeds."""
    steps = _make_steps("pytest", "mypy")
    with patch(_PATCH, return_value=_result(0)):
        run_steps(steps)
    captured = capsys.readouterr()
    assert captured.err == ""


# ---------------------------------------------------------------------------
# Exit code
# ---------------------------------------------------------------------------

def test_exit_code_zero_when_all_pass() -> None:
    steps = _make_steps("pytest", "mypy")
    with patch(_PATCH, return_value=_result(0)):
        assert run_steps(steps) == 0


def test_exit_code_nonzero_when_step_fails() -> None:
    steps = _make_steps("mypy")
    with patch(_PATCH, return_value=_result(2)):
        assert run_steps(steps) != 0


def test_exit_code_reflects_tool_returncode() -> None:
    """The exact return code of the failing tool is propagated."""
    steps = _make_steps("tsc")
    with patch(_PATCH, return_value=_result(42)):
        assert run_steps(steps) == 42


# ---------------------------------------------------------------------------
# No .venv executables (WDAC — ADR-015)
# ---------------------------------------------------------------------------

def test_no_venv_executable_in_any_step() -> None:
    """No step calls a console-script launcher such as `.venv/Scripts/pytest.exe`.

    The interpreter itself is allowed: it is what `uv run python` runs, and the
    only way to reach the project's pytest and mypy (`<interpreter> -m tool`).
    """
    for step in STEPS:
        programme, *args = step.cmd
        assert programme == sys.executable or Path(programme).stem == "npx", (
            f"Step {step.name!r} starts with {programme!r}"
        )
        for part in args:
            assert ".venv" not in part, (
                f"Step {step.name!r} contains a .venv path in its command: {part!r}"
            )


def test_python_steps_use_the_running_interpreter() -> None:
    """`python` alone is the system interpreter on Windows, without pytest."""
    for step in STEPS:
        if step.name in ("pytest", "mypy"):
            assert step.cmd[0] == sys.executable


# ---------------------------------------------------------------------------
# Parallel pytest (ticket-357)
# ---------------------------------------------------------------------------


def test_pytest_runs_on_several_workers_when_xdist_is_installed() -> None:
    from verifier import pytest_command

    with patch("verifier.importlib.util.find_spec", return_value=MagicMock()):
        cmd = pytest_command()

    assert cmd[:3] == [sys.executable, "-m", "pytest"]
    assert cmd[cmd.index("-n") + 1] == "8"


def test_pytest_runs_serially_when_xdist_is_missing() -> None:
    from verifier import pytest_command

    with patch("verifier.importlib.util.find_spec", return_value=None):
        cmd = pytest_command()

    assert "-n" not in cmd
    assert cmd[:3] == [sys.executable, "-m", "pytest"]


def test_xdist_is_a_dev_dependency() -> None:
    pyproject = (Path(__file__).resolve().parent.parent / "pyproject.toml").read_text(
        encoding="utf-8"
    )
    assert '"pytest-xdist' in pyproject


# ---------------------------------------------------------------------------
# Parallel chains (ticket-351)
# ---------------------------------------------------------------------------


def test_backend_and_frontend_steps_are_defined() -> None:
    """BACKEND_STEPS and FRONTEND_STEPS are both non-empty with the right steps."""
    assert {s.name for s in BACKEND_STEPS} == {"pytest", "mypy"}
    assert {s.name for s in FRONTEND_STEPS} == {"tsc", "eslint", "vitest"}


def test_steps_equals_backend_plus_frontend() -> None:
    """The legacy STEPS list is exactly BACKEND_STEPS followed by FRONTEND_STEPS."""
    assert STEPS == BACKEND_STEPS + FRONTEND_STEPS


def test_chains_overlap_in_time() -> None:
    """Backend and frontend chains run concurrently.

    Uses a shared counter under a lock: if more than one subprocess call is
    active at the same time, the chains are truly parallel.
    """
    active: list[str] = []
    lock = threading.Lock()
    overlapped = threading.Event()
    DELAY = 1.0

    def slow_run(cmd: list[str], **_: object) -> MagicMock:
        step_id = " ".join(cmd)
        with lock:
            active.append(step_id)
            if len(active) > 1:
                overlapped.set()
        time.sleep(DELAY)
        with lock:
            active.remove(step_id)
        return _result(0)

    backend = [Step("pytest", ["python", "-m", "pytest"], _FAKE_BACKEND)]
    frontend = [Step("vitest", ["npx", "vitest", "run"], _FAKE_FRONTEND)]

    with patch(_PATCH, side_effect=slow_run):
        rc = run_parallel(backend, frontend)

    assert overlapped.is_set(), "backend and frontend chains never ran at the same time"
    assert rc == 0


def test_backend_failure_does_not_stop_frontend_chain() -> None:
    """A failure in the backend chain lets the frontend chain run to completion."""
    call_counts: dict[str, int] = {"backend": 0, "frontend": 0}

    def stubbed_run(cmd: list[str], *, cwd: Path, **_: object) -> MagicMock:
        if cwd == _FAKE_BACKEND:
            call_counts["backend"] += 1
            return _result(1, "backend error")
        call_counts["frontend"] += 1
        return _result(0)

    backend = _make_steps("pytest")
    frontend = _make_steps("tsc", "eslint", "vitest")

    with patch(_PATCH, side_effect=stubbed_run):
        rc = run_parallel(backend, frontend)

    assert rc != 0, "exit code must be non-zero when backend fails"
    assert call_counts["backend"] == 1, "backend should have run exactly once"
    assert call_counts["frontend"] == 3, "all 3 frontend steps should have run"


def test_chain_head_failure_stops_remaining_chain_steps() -> None:
    """A failure at the head of a chain prevents subsequent steps from running."""
    call_count = 0

    def stubbed_run(cmd: list[str], **_: object) -> MagicMock:
        nonlocal call_count
        call_count += 1
        return _result(1, "error")

    backend = _make_steps("pytest", "mypy")
    with patch(_PATCH, side_effect=stubbed_run):
        _run_chain(backend)

    assert call_count == 1, f"only the first step should run, got {call_count} call(s)"


def test_report_names_both_failing_steps(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """When both chains fail, stderr names each failing step (backend first)."""
    def stubbed_run(cmd: list[str], *, cwd: Path, **_: object) -> MagicMock:
        if cwd == _FAKE_BACKEND:
            return _result(1, "pytest error", "")
        return _result(1, "tsc error", "")

    backend = _make_steps("pytest")
    frontend = _make_steps("tsc")

    with patch(_PATCH, side_effect=stubbed_run):
        rc = run_parallel(backend, frontend)

    captured = capsys.readouterr()
    assert "pytest" in captured.err, "backend failure not reported"
    assert "tsc" in captured.err, "frontend failure not reported"
    assert captured.err.index("pytest") < captured.err.index("tsc"), (
        "backend failure should appear before frontend failure"
    )
    assert rc != 0


def test_run_parallel_returns_zero_when_all_pass() -> None:
    """Exit code is 0 when both chains succeed."""
    backend = _make_steps("pytest", "mypy")
    frontend = _make_steps("tsc", "eslint", "vitest")
    with patch(_PATCH, return_value=_result(0)):
        assert run_parallel(backend, frontend) == 0
