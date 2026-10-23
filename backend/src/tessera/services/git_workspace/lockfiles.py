"""Lockfile detection and the one-line summary of their diffs."""

import re
from pathlib import Path


#: Lockfile names whose diff content is replaced by a one-line summary when
#: fed to reviewing agents.  The commit itself is not affected — lockfiles are
#: committed in full.  A single entry here covers every subdirectory
#: (``backend/uv.lock`` matches ``uv.lock``).
LOCKFILE_NAMES: frozenset[str] = frozenset({
    "uv.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "poetry.lock",
    "Cargo.lock",
})


# Captures the destination path from ``diff --git a/<src> b/<dst>``.
_DIFF_GIT_RE = re.compile(r"^diff --git a/.+ b/(.+)$")


def _is_lockfile(path: str) -> bool:
    """True if the path's filename matches a known lockfile."""
    return Path(path).name in LOCKFILE_NAMES


def _resumer_lockfiles(diff: str) -> str:
    """Replace lockfile sections in a unified diff with a one-line summary.

    For each known lockfile, the full hunk content is replaced by:
      ``<path>: lockfile modified, N lines added, M deleted``

    Non-lockfile sections are left untouched.  This only filters what
    reviewing agents see — the commit itself is not affected.
    """
    if not diff:
        return diff

    lines = diff.splitlines(keepends=True)
    output: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]
        if not line.startswith("diff --git "):
            output.append(line)
            i += 1
            continue

        # Determine file path from the ``diff --git`` header.
        m = _DIFF_GIT_RE.match(line.rstrip("\n"))
        file_path = m.group(1) if m else ""

        # Scan the metadata header lines (index, ---, +++) for a better path.
        j = i + 1
        while j < len(lines) and not lines[j].startswith(("diff --git ", "@@")):
            if lines[j].startswith("+++ b/"):
                file_path = lines[j][6:].rstrip("\n")
            j += 1
        # ``j`` now points to the first hunk line (``@@``) or next file section.

        if not _is_lockfile(file_path):
            # Keep diff --git line, metadata header, and all hunk lines.
            output.append(lines[i])
            i += 1
            while i < len(lines) and not lines[i].startswith("diff --git "):
                output.append(lines[i])
                i += 1
            continue

        # Lockfile: skip header, count added/removed hunk lines, emit summary.
        i = j
        added = removed = 0
        while i < len(lines) and not lines[i].startswith("diff --git "):
            hunk_line = lines[i]
            if hunk_line.startswith("+") and not hunk_line.startswith("+++"):
                added += 1
            elif hunk_line.startswith("-") and not hunk_line.startswith("---"):
                removed += 1
            i += 1

        output.append(
            f"{file_path}: lockfile modified, {added} lines added, {removed} deleted\n"
        )

    return "".join(output)
