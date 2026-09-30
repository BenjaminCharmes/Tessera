"""Snapshot and diff of artifact directories for design tickets — ticket-274.

On projects where artifacts are local (tickets/ and memory/ excluded from git),
the git diff seen by the reviewer and validator contains nothing the architect
wrote.  Even on tracked projects, tickets/ is excluded from the diff by
construction (``_ORCHESTRATOR_ARTIFACT_PATHS`` in git_workspace.py).

This module takes a text snapshot of memory/ and tickets/ at run start, then
computes a textual diff to be appended to the material given to the reviewer
and validator (not the security auditor, which focuses on code).

The diff is intentionally excluded from commits: it describes what Tessera's
own artifact directories contain, not code the coder agent produced.
"""
import difflib
from pathlib import Path

# Artifact directories to snapshot.
_ARTIFACT_DIRS: tuple[str, ...] = ("memory", "tickets")

# Only files with these extensions are considered text artifacts.
_TEXT_EXTENSIONS: frozenset[str] = frozenset({".md", ".yaml", ".yml", ".json", ".txt"})


def snapshot_artifacts(project_path: Path) -> dict[str, str]:
    """Read the current content of memory/ and tickets/ trees.

    Returns a mapping {relative_posix_path: content} for all text files in the
    artifact directories.  Called once at run start; the result is stored in
    ``PipelineRun.artifact_snapshot`` and compared at the end of each coder
    turn to produce the artifact diff.
    """
    result: dict[str, str] = {}
    for dir_name in _ARTIFACT_DIRS:
        dir_path = project_path / dir_name
        if not dir_path.is_dir():
            continue
        for file_path in sorted(dir_path.rglob("*")):
            if not file_path.is_file():
                continue
            if file_path.suffix not in _TEXT_EXTENSIONS:
                continue
            rel = file_path.relative_to(project_path).as_posix()
            try:
                result[rel] = file_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                pass
    return result


def diff_artifacts(before: dict[str, str], project_path: Path) -> str:
    """Compute a textual diff between ``before`` snapshot and current artifact state.

    Returns a labeled section suitable for appending to the reviewed material
    passed to the reviewer and validator.  Returns an empty string when nothing
    changed, so callers can skip the section without adding noise.

    The diff covers new files, deleted files, and modified files alike.
    """
    after = snapshot_artifacts(project_path)
    all_paths = sorted(set(before) | set(after))

    parts: list[str] = []
    for path in all_paths:
        before_content = before.get(path, "")
        after_content = after.get(path, "")
        if before_content == after_content:
            continue

        diff_lines = list(
            difflib.unified_diff(
                before_content.splitlines(keepends=True),
                after_content.splitlines(keepends=True),
                fromfile=f"a/{path}",
                tofile=f"b/{path}",
            )
        )
        if diff_lines:
            parts.append("".join(diff_lines))

    if not parts:
        return ""

    return (
        "\n\n## Artefacts modifiés (décisions et tickets, non versionnés)\n"
        + "\n".join(parts)
    )
