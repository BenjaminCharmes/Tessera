"""Tests for the fastapi-react project template (ticket-372).

Verifies structural constraints (no build artefacts, known markers only)
and, in an integration test, that the template builds and its tests pass
after placeholder substitution.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

# Path to the template from this test file:  backend/tests/ → backend/ → tessera/ → templates/
TEMPLATE_DIR = Path(__file__).parent.parent.parent / "templates" / "fastapi-react"

ALLOWED_MARKERS: frozenset[str] = frozenset(
    {
        "{{project_id}}",
        "{{project_name}}",
        "{{backend_port}}",
        "{{frontend_port}}",
    }
)

_MARKER_RE = re.compile(r"\{\{[^}]+\}\}")

_FORBIDDEN_DIR_NAMES: frozenset[str] = frozenset(
    {"node_modules", "dist", ".venv", "uv.lock"}
)
_FORBIDDEN_EXTENSIONS: frozenset[str] = frozenset({".db"})


def _template_files() -> list[Path]:
    """Return all files inside the template directory."""
    return [p for p in TEMPLATE_DIR.rglob("*") if p.is_file()]


def test_template_dir_exists() -> None:
    """Sanity check: the template directory must be present."""
    assert TEMPLATE_DIR.is_dir(), f"Template not found: {TEMPLATE_DIR}"


def test_no_forbidden_paths() -> None:
    """The template must not contain node_modules, dist, .venv, uv.lock or .db files."""
    violations: list[str] = []
    for path in TEMPLATE_DIR.rglob("*"):
        # Check every path component against forbidden directory names
        for part in path.relative_to(TEMPLATE_DIR).parts:
            if part in _FORBIDDEN_DIR_NAMES:
                violations.append(str(path.relative_to(TEMPLATE_DIR)))
                break
        # Check file extension
        if path.is_file() and path.suffix in _FORBIDDEN_EXTENSIONS:
            violations.append(str(path.relative_to(TEMPLATE_DIR)))

    assert not violations, (
        "Template contains forbidden paths:\n" + "\n".join(violations)
    )


def test_only_known_markers() -> None:
    """Every {{…}} placeholder in the template must be one of the four allowed markers."""
    unknown: list[tuple[str, str]] = []
    for path in _template_files():
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue  # binary files cannot contain text markers
        for match in _MARKER_RE.findall(content):
            if match not in ALLOWED_MARKERS:
                unknown.append((str(path.relative_to(TEMPLATE_DIR)), match))

    assert not unknown, (
        "Unknown markers found in template:\n"
        + "\n".join(f"  {file}: {marker}" for file, marker in unknown)
    )


def _replace_markers(dest: Path, replacements: dict[str, str]) -> None:
    """Replace all markers in every text file under dest."""
    for path in dest.rglob("*"):
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        new_content = content
        for marker, value in replacements.items():
            new_content = new_content.replace(marker, value)
        if new_content != content:
            path.write_text(new_content, encoding="utf-8")


@pytest.mark.integration
def test_integration_template_builds_and_tests_pass(tmp_path: Path) -> None:
    """Copy the template, substitute markers, install dependencies and verify.

    Checks (in order):
    - frontend: typecheck, lint, vitest, build
    - backend: mypy, pytest

    This test installs npm and Python packages — it takes several minutes
    and is excluded from the default suite.  Run it manually before merge:
        uv run pytest -m integration backend/tests/test_gabarit_fastapi_react.py
    """
    dest = tmp_path / "project"
    shutil.copytree(TEMPLATE_DIR, dest)

    replacements: dict[str, str] = {
        "{{project_id}}": "test-project",
        "{{project_name}}": "Test Project",
        "{{backend_port}}": "8099",
        "{{frontend_port}}": "5099",
    }
    _replace_markers(dest, replacements)

    backend_dir = dest / "backend"
    frontend_dir = dest / "frontend"

    # Sous Windows, npm est `npm.cmd` : `subprocess` ne le trouve pas sans son
    # chemin complet, que `shutil.which` résout.
    npm = shutil.which("npm")
    assert npm is not None, "npm introuvable dans le PATH"

    # --- Frontend ---
    subprocess.run([npm, "install"], cwd=frontend_dir, check=True)
    subprocess.run([npm, "run", "typecheck"], cwd=frontend_dir, check=True)
    subprocess.run([npm, "run", "lint"], cwd=frontend_dir, check=True)
    subprocess.run([npm, "run", "test"], cwd=frontend_dir, check=True)
    subprocess.run([npm, "run", "build"], cwd=frontend_dir, check=True)

    # --- Backend ---
    # `python -m` comme dans la test_command des projets : WDAC bloque les
    # lanceurs .exe de mypy et pytest.
    subprocess.run(["uv", "sync"], cwd=backend_dir, check=True)
    subprocess.run(["uv", "run", "python", "-m", "mypy", "."], cwd=backend_dir, check=True)
    subprocess.run(["uv", "run", "python", "-m", "pytest", "-q"], cwd=backend_dir, check=True)
