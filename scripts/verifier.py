"""Verification script: runs backend and frontend checks in parallel chains.

Backend chain (pytest → mypy) and frontend chain (tsc → eslint → vitest) run
side by side, each stopping at its first failure. Outputs are captured and
printed together once both chains finish — never interleaved.

Run from backend/ with: uv run python ../scripts/verifier.py

Never calls a console-script launcher (`pytest.exe`, `mypy.exe`): Windows
application control refuses them (os error 4551). Python tools run as
`<interpreter> -m <tool>`, with the interpreter that runs this script.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"

# `python` seul désigne, sous Windows, l'interpréteur du système et non celui
# du `.venv` : pytest et mypy n'y sont pas. `npx` est un `.cmd`, qu'un
# `subprocess` sans shell ne trouve pas sous son nom court.
_PYTHON = sys.executable
_NPX = "npx.cmd" if os.name == "nt" else "npx"

# 1 973 tests en série prenaient douze minutes, et la suite complète
# dépassait les 900 s du testeur à elle seule (ticket-357). Huit processus la
# ramènent à deux minutes et demie sans saturer une machine qui fait tourner
# d'autres files.
_PYTEST_WORKERS = "8"

# Ligne max renvoyée au codeur pour ne pas inonder sa fenêtre.
_MAX_LINES = 120


@dataclass
class Step:
    name: str
    cmd: list[str]
    cwd: Path


def pytest_command() -> list[str]:
    """Return the pytest command, spread over several workers when xdist is installed."""
    cmd = [_PYTHON, "-m", "pytest", "-q", "-x", "-m", "not integration"]
    # Sans xdist (environnement synchronisé sans l'extra `dev`), la suite
    # tourne en série plutôt que d'échouer sur une option inconnue.
    if importlib.util.find_spec("xdist") is not None:
        cmd += ["-n", _PYTEST_WORKERS]
    return cmd


BACKEND_STEPS: list[Step] = [
    Step(
        name="pytest",
        cmd=pytest_command(),
        cwd=BACKEND_DIR,
    ),
    Step(
        name="mypy",
        cmd=[_PYTHON, "-m", "mypy", "src/"],
        cwd=BACKEND_DIR,
    ),
]

FRONTEND_STEPS: list[Step] = [
    Step(
        name="tsc",
        cmd=[_NPX, "tsc", "-b"],
        cwd=FRONTEND_DIR,
    ),
    Step(
        name="eslint",
        cmd=[_NPX, "eslint", "."],
        cwd=FRONTEND_DIR,
    ),
    Step(
        name="vitest",
        cmd=[_NPX, "vitest", "run"],
        cwd=FRONTEND_DIR,
    ),
]

# Kept for backward compatibility and for tools that iterate all steps.
STEPS: list[Step] = BACKEND_STEPS + FRONTEND_STEPS


def _extract_errors(output: str) -> str:
    """Return the most relevant lines, capped to avoid flooding the codeur."""
    lines = output.splitlines()
    if len(lines) <= _MAX_LINES:
        return output
    # La fin porte le résumé et le test en échec : c'est elle qu'on garde.
    omitted = len(lines) - _MAX_LINES
    return "\n".join([f"… ({omitted} ligne(s) omise(s))", *lines[-_MAX_LINES:]])


@dataclass
class _StepFailure:
    step_name: str
    returncode: int
    excerpt: str


def _run_chain(steps: list[Step]) -> list[_StepFailure]:
    """Run steps sequentially; stop at first failure and return it.

    Returns a list with at most one entry: the failing step, with its
    return code and extracted output. Returns an empty list when all pass.
    """
    for step in steps:
        result = subprocess.run(
            step.cmd,
            cwd=step.cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            combined = result.stdout + result.stderr
            return [_StepFailure(step.name, result.returncode, _extract_errors(combined))]
    return []


def run_parallel(backend_steps: list[Step], frontend_steps: list[Step]) -> int:
    """Run backend and frontend chains concurrently; return non-zero if either fails.

    Each chain is sequential and stops at its first failure. Outputs are
    captured independently — never interleaved. The report (backend first)
    is printed to stderr once both chains finish.
    """
    with ThreadPoolExecutor(max_workers=2) as executor:
        backend_future = executor.submit(_run_chain, backend_steps)
        frontend_future = executor.submit(_run_chain, frontend_steps)
        backend_failures = backend_future.result()
        frontend_failures = frontend_future.result()

    all_failures = backend_failures + frontend_failures
    for failure in all_failures:
        print(f"{failure.step_name} :\n{failure.excerpt}", file=sys.stderr)

    return all_failures[0].returncode if all_failures else 0


def run_steps(steps: list[Step]) -> int:
    """Run all steps in order; stop and report the first failure.

    Returns the exit code of the first failing step, or 0 if all pass.
    Kept for backward compatibility with tests and tooling that calls it directly.
    """
    for step in steps:
        result = subprocess.run(
            step.cmd,
            cwd=step.cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            combined = result.stdout + result.stderr
            print(f"{step.name} :\n{_extract_errors(combined)}", file=sys.stderr)
            return result.returncode
    return 0


def main() -> int:
    """Entry point."""
    return run_parallel(BACKEND_STEPS, FRONTEND_STEPS)


if __name__ == "__main__":
    sys.exit(main())
