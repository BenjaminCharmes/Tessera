"""Warning when a project's test command never runs its build (ticket-454).

A build-only error (bundler, framework typing, assets) crosses every gate of
the pipeline when the declared `test_command` does not build: only the CI
sees it. This module only detects the gap; the run goes on.
"""
import json
from pathlib import Path

from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

_IGNORED_DIRS: frozenset[str] = frozenset({"node_modules"})


def _has_build_script(package_json: Path) -> bool:
    """True when the file is a readable package.json declaring `scripts.build`."""
    try:
        data = json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if not isinstance(data, dict):
        return False
    scripts = data.get("scripts")
    return isinstance(scripts, dict) and "build" in scripts


def _candidate_dirs(project_path: Path) -> list[Path]:
    """The project root, then its first-level sub-folders (sorted)."""
    try:
        children = sorted(
            child
            for child in project_path.iterdir()
            if child.is_dir()
            and not child.name.startswith(".")
            and child.name not in _IGNORED_DIRS
        )
    except OSError as exc:
        _logger.warning("build_warning_scan_failed", extra={"error": str(exc)})
        children = []
    return [project_path, *children]


def folders_with_build_script(project_path: Path) -> list[str]:
    """Names of the folders (root included) whose package.json has a build."""
    return [
        folder.name
        for folder in _candidate_dirs(project_path)
        if _has_build_script(folder / "package.json")
    ]


def build_warnings(project_path: Path, test_command: str | None) -> list[str]:
    """One warning line per folder whose build the test command skips.

    Empty when the command mentions `build` (`run build`, `check:build`) or
    when no package.json declares a build script.
    """
    if "build" in (test_command or ""):
        return []
    return [
        f"test_command ne lance pas le build de {dossier} : "
        "une erreur de build passera jusqu'à la CI"
        for dossier in folders_with_build_script(project_path)
    ]
