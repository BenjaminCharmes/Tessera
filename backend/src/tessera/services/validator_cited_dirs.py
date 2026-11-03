# -*- coding: utf-8 -*-
"""Folders cited by acceptance criteria, joined as a file list (ticket-509).

A criterion such as "the mockup exists in `design/maquette/`" cannot be read
as a file: the validator gets the names of the files the folder holds, on one
level, not their content.
"""
import re
from pathlib import Path

# Max number of files named in one folder entry.
FOLDER_MAX_ENTRIES = 100

# Relative path made of plain segments, optionally ending with a slash.
_FOLDER_SHAPE = re.compile(r"^[\w.\-]+(?:/[\w.\-]+)*/?$")


def looks_like_folder(candidate: str) -> bool:
    """Whether ``candidate`` reads as a folder path (``design/maquette/``).

    A path needs a ``/`` and plain segments. A leading slash (an URL route),
    a scheme or a space rule it out. The token may well name a file: the
    caller looks for a folder first, then for a file.
    """
    return "/" in candidate and _FOLDER_SHAPE.match(candidate) is not None


def resolve_folder(ref: str, root: Path) -> Path | None:
    """Resolve ``ref`` as an existing folder under ``root``, never outside it."""
    if Path(ref).is_absolute() or ".." in Path(ref).parts:
        return None
    candidate = root / ref.rstrip("/")
    if not candidate.is_dir():
        return None
    try:
        candidate.resolve().relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def list_folder_files(ref: str, folder: Path) -> list[str]:
    """Relative paths of the files directly inside ``folder``, sorted."""
    prefix = ref.rstrip("/")
    return sorted(
        f"{prefix}/{child.name}" for child in folder.iterdir() if child.is_file()
    )


def render_folder_entry(
    ref: str, files: list[str], budget: int
) -> tuple[str, bool]:
    """Section entry of a folder, and whether its list was cut.

    The list is cut at ``FOLDER_MAX_ENTRIES`` names, then at ``budget``
    characters; a mention says how many names are left out.
    """
    shown = files[:FOLDER_MAX_ENTRIES]
    body = "\n".join(shown)
    cut = len(files) > len(shown)
    if len(body) > budget:
        body = body[: max(budget, 0)]
        cut = True
    if cut:
        body += f"\n[... liste tronquée, {len(files)} fichiers au total]"
    head = f"### {ref}\n*(dossier, {len(files)} fichiers)*"
    return f"{head}\n```\n{body}\n```", cut
