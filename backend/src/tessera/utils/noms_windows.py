"""Normalisation des noms de fichiers à la manière de Win32 — ticket-747.

Windows ne distingue pas `settings.json`, `Settings.JSON`, `settings.json.`,
`settings.json ` ni `settings.json::$DATA` : tous ouvrent le même fichier. Or
`Path.resolve()` ne normalise rien quand la cible n'existe pas encore, et un
garde qui compare le nom exact laisse passer ces variantes. Les gardes de
chemins protégés comparent donc la forme normalisée, jamais le nom brut.
"""
from pathlib import Path


def normaliser_segment(segment: str) -> str:
    """Return the form Win32 would open for a path segment, case-folded.

    Drops an NTFS stream suffix (`::$DATA`), then trailing dots and spaces.
    """
    sans_flux = segment.split("::", 1)[0]
    return sans_flux.rstrip(". ").casefold()


def normaliser_segments(chemin: Path) -> tuple[str, ...]:
    """Normalise every segment of a path, anchor included (it is left intact)."""
    return tuple(normaliser_segment(partie) for partie in chemin.parts)
