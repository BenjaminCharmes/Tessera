"""The backend stays clean under ruff — ticket-773."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parent.parent


def _version_epinglee() -> str:
    """Return the ruff version pinned in the dev dependencies of pyproject.toml."""
    texte = (_BACKEND / "pyproject.toml").read_text(encoding="utf-8")
    trouve = re.search(r'"ruff==([\d.]+)"', texte)
    assert trouve, "ruff must be pinned in the dev dependencies"
    return trouve.group(1)


def test_ruff_check_passes_on_src_and_tests() -> None:
    exe = shutil.which("ruff")
    if exe is None:
        pytest.skip("ruff is not installed in this environment")
    version = subprocess.run([exe, "--version"], capture_output=True, text=True).stdout
    # Un autre ruff dans le PATH n'a pas les mêmes règles : on ne le juge pas.
    if version.split()[-1:] != [_version_epinglee()]:
        pytest.skip(f"ruff on PATH is {version.strip()}, not the pinned version")
    resultat = subprocess.run(
        [exe, "check", "src", "tests", "--no-cache"],
        cwd=_BACKEND,
        capture_output=True,
        text=True,
    )
    assert resultat.returncode == 0, resultat.stdout + resultat.stderr
