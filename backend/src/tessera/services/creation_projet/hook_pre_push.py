"""Install the forbidden-terms `pre-push` hook in a project repository (ADR-048).

The hook of a project is a two-line wrapper that runs Tessera's own
`scripts/hooks/pre-push` by absolute path, with the same arguments and the same
standard input. A `professional` project gets none (ADR-048), and a different
`pre-push` already in place is never overwritten.
"""
import stat
import sys
from enum import Enum
from pathlib import Path

from tessera.services.projets.manifeste import lire_chaine
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Racine du dépôt Tessera : backend/src/tessera/services/creation_projet/ -> 5 niveaux.
_RACINE_TESSERA = Path(__file__).resolve().parents[5]


class EtatHook(str, Enum):
    """What `installer_hook` did for one project."""

    INSTALLE = "installe"
    DEJA_PRESENT = "deja_present"
    PROFESSIONNEL = "professionnel"
    SANS_DEPOT = "sans_depot"
    DIFFERENT = "different"


def contenu_hook(racine_tessera: Path, python: str = "python3") -> str:
    """The wrapper script: runs Tessera's hook, forwarding arguments and stdin."""
    script = (racine_tessera / "scripts" / "hooks" / "pre-push").as_posix()
    return f'#!/bin/sh\nexec {python} "{script}" "$@"\n'


def installer_hook(
    projet: Path, racine_tessera: Path = _RACINE_TESSERA, python: str = "python3"
) -> EtatHook:
    """Write `.git/hooks/pre-push` in `projet`, unless there is a reason not to."""
    if lire_chaine(projet, "confidentiality") == "professional":
        return EtatHook.PROFESSIONNEL
    dossier_git = projet / ".git"
    if not dossier_git.is_dir():
        return EtatHook.SANS_DEPOT
    cible = dossier_git / "hooks" / "pre-push"
    contenu = contenu_hook(racine_tessera, python)
    if cible.exists():
        lu = cible.read_text(encoding="utf-8", errors="replace")
        return EtatHook.DEJA_PRESENT if lu == contenu else EtatHook.DIFFERENT
    cible.parent.mkdir(parents=True, exist_ok=True)
    # `newline=""` : un LF sous Windows, sinon `sh` lit `python3\r`.
    with cible.open("w", encoding="utf-8", newline="") as f:
        f.write(contenu)
    cible.chmod(cible.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    _logger.info("pre_push_hook_installed", extra={"project": projet.name})
    return EtatHook.INSTALLE


def installer_sur_tous(workspace: Path) -> dict[str, EtatHook]:
    """Install the hook in every project folder of `workspace`; the state of each."""
    if not workspace.is_dir():
        return {}
    return {
        d.name: installer_hook(d)
        for d in sorted(workspace.iterdir())
        if d.is_dir() and not d.name.startswith(".")
    }


def main(workspace: Path) -> int:
    """Print what was done for each project; exit 1 if a foreign hook was left alone."""
    resultats = installer_sur_tous(workspace)
    for nom, etat in resultats.items():
        sys.stdout.write(f"{nom} : {etat.value}" + chr(10))
    if not resultats:
        sys.stdout.write(f"Aucun projet dans {workspace}" + chr(10))
    return 1 if EtatHook.DIFFERENT in resultats.values() else 0


if __name__ == "__main__":
    from tessera.config import settings

    sys.exit(main(settings.ide_workspace_dir))
