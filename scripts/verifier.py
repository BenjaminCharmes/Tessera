"""Verification script: runs pytest, mypy and frontend checks in order.

Stops at the first failing step and prints its name followed by the tool output.
Run from backend/ with: uv run python ../scripts/verifier.py

Never calls a console-script launcher (`pytest.exe`, `mypy.exe`): Windows
application control refuses them (os error 4551). Python tools run as
`<interpreter> -m <tool>`, with the interpreter that runs this script.
"""
from __future__ import annotations

import os
import subprocess
import sys
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

# Ligne max renvoyée au codeur pour ne pas inonder sa fenêtre.
_MAX_LINES = 120


@dataclass
class Step:
    name: str
    cmd: list[str]
    cwd: Path


STEPS: list[Step] = [
    Step(
        name="pytest",
        cmd=[_PYTHON, "-m", "pytest", "-q", "-x", "-m", "not integration"],
        cwd=BACKEND_DIR,
    ),
    Step(
        name="mypy",
        cmd=[_PYTHON, "-m", "mypy", "src/"],
        cwd=BACKEND_DIR,
    ),
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


def _extract_errors(output: str) -> str:
    """Return the most relevant lines, capped to avoid flooding the codeur."""
    lines = output.splitlines()
    if len(lines) <= _MAX_LINES:
        return output
    # La fin porte le résumé et le test en échec : c'est elle qu'on garde.
    omitted = len(lines) - _MAX_LINES
    return "\n".join([f"… ({omitted} ligne(s) omise(s))", *lines[-_MAX_LINES:]])


def run_steps(steps: list[Step]) -> int:
    """Run all steps in order; stop and report the first failure.

    Returns the exit code of the first failing step, or 0 if all pass.
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
    return run_steps(STEPS)


if __name__ == "__main__":
    sys.exit(main())
