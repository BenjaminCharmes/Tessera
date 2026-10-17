"""Recognise, in the output of a failed step, that a *tool* is missing.

A step whose launcher starts but whose tool does not (``pnpm tsc`` with a
broken ``node_modules``) exits non-zero like a red test. This module tells the
two apart so the coder is not sent to fix code that is not at fault
(ticket-496).
"""

import re
from pathlib import Path

# Chaque motif capture le nom de l'outil dans son premier groupe.
_PNPM = re.compile(
    r"ERR_PNPM_RECURSIVE_EXEC_FIRST_FAIL\s+Command \"([^\"]+)\" not found"
)
# `sh: 1: tsc: not found`, `bash: line 1: tsc: command not found`.
_SHELL = re.compile(
    r"^\s*\w*sh: (?:line \d+: )?(?:\d+: )?([\w.@/+-]+): (?:command )?not found\s*$",
    re.MULTILINE,
)
_WINDOWS = re.compile(r"'([^']+)' is not recognized as an internal or external command")
_MODULE = re.compile(r"Cannot find module '([^']+)'")

_SEGMENT = "node_modules/"


def outil_introuvable(sortie: str, dossier: Path, projet: Path | None = None) -> str | None:
    """Return the missing tool's name found in ``sortie``, or ``None``.

    ``dossier`` is where the step ran and ``projet`` the project root: a
    ``node_modules`` path outside both is a stale link. A module of the
    project's own code (outside ``node_modules``) is never a missing tool.
    """
    for motif in (_PNPM, _SHELL, _WINDOWS):
        trouve = motif.search(sortie)
        if trouve:
            return trouve.group(1)
    racines = [dossier] if projet is None else [dossier, projet]
    for trouve in _MODULE.finditer(sortie):
        nom = _module_manquant(trouve.group(1), dossier, racines)
        if nom:
            return nom
    return None


def _module_manquant(cite: str, dossier: Path, racines: list[Path]) -> str | None:
    """Name of the package when ``cite`` is a dead or foreign ``node_modules`` path."""
    normalise = cite.replace("\\", "/")
    position = normalise.rfind(_SEGMENT)
    if position < 0:
        return None
    chemin = Path(cite)
    if not chemin.is_absolute():
        chemin = dossier / chemin
    if chemin.exists() and any(chemin.resolve().is_relative_to(r.resolve()) for r in racines):
        return None
    return _nom_du_paquet(normalise[position + len(_SEGMENT):])


def _nom_du_paquet(reste: str) -> str | None:
    """First path component after ``node_modules/``, scope included."""
    parts = [p for p in reste.split("/") if p]
    if not parts:
        return None
    if parts[0].startswith("@") and len(parts) > 1:
        return f"{parts[0]}/{parts[1]}"
    return parts[0]
