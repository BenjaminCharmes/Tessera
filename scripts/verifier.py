"""Verification script: runs pytest, mypy and frontend checks in order.

Stops at the first failing step and prints its name followed by the tool output.
Run from backend/ with: uv run python ../scripts/verifier.py

Skips all .venv executables — WDAC blocks them on Windows (ADR-015).
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"

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
        cmd=["python", "-m", "pytest", "-q", "-x", "-m", "not integration"],
        cwd=BACKEND_DIR,
    ),
    Step(
        name="mypy",
        cmd=["python", "-m", "mypy", "src/"],
        cwd=BACKEND_DIR,
    ),
    Step(
        name="tsc",
        cmd=["npx", "tsc", "-b"],
        cwd=FRONTEND_DIR,
    ),
    Step(
        name="eslint",
        cmd=["npx", "eslint", "."],
        cwd=FRONTEND_DIR,
    ),
    Step(
        name="vitest",
        cmd=["npx", "vitest", "run"],
        cwd=FRONTEND_DIR,
    ),
]


def _extract_errors(output: str) -> str:
    """Return the most relevant lines, capped to avoid flooding the codeur."""
    lines = output.splitlines()
    if len(lines) <= _MAX_LINES:
        return output
    head = lines[:_MAX_LINES]
    omitted = len(lines) - _MAX_LINES
    head.append(f"… ({omitted} ligne(s) omise(s))")
    return "\n".join(head)


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
