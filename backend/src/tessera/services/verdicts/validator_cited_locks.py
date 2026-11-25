"""Lockfiles cited by a criterion: joined by their diff, never by content.

A lockfile weighs hundreds of thousands of characters; the cited-files
budget would keep only its head (ticket-1030).
"""
import re
from pathlib import Path

LOCKFILE_NAMES = frozenset(
    {
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "uv.lock",
        "poetry.lock",
        "Cargo.lock",
    }
)

_DIFF_HEADER = re.compile(r"^diff --git a/(.+?) b/(.+)$", re.MULTILINE)


def is_lockfile(ref: str) -> bool:
    """True when ``ref`` names a known dependency lockfile."""
    return Path(ref).name in LOCKFILE_NAMES


def _same_file(ref: str, path: str) -> bool:
    return path == ref or path.endswith("/" + ref)


def extract_file_diff(diff: str, ref: str) -> str:
    """The part of a unified ``diff`` that concerns ``ref``; empty if none."""
    headers = list(_DIFF_HEADER.finditer(diff))
    parts: list[str] = []
    for i, header in enumerate(headers):
        if not _same_file(ref, header.group(2)):
            continue
        end = headers[i + 1].start() if i + 1 < len(headers) else len(diff)
        parts.append(diff[header.start():end].rstrip("\n"))
    return "\n".join(parts)


def render_lockfile_entry(ref: str, diff: str, budget: int) -> tuple[str, bool]:
    """Section entry for a cited lockfile and whether its diff was cut."""
    part = extract_file_diff(diff, ref)
    if not part:
        return f"### {ref}\n*(verrou cité, non modifié par le run)*", False
    cut = len(part) > budget
    if cut:
        part = part[:budget] + f"\n[... {len(part) - budget} caractères tronqués]"
    return f"### {ref} (diff du run)\n```diff\n{part}\n```", cut
