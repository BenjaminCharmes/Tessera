"""Install the forbidden-terms `pre-push` hook in a project repository (ADR-048).

The hook of a project is a two-line wrapper that runs Tessera's own
`scripts/hooks/pre-push` by absolute path, with the same arguments and the same
standard input. A `professional` project gets none (ADR-048), and a different
`pre-push` already in place is never overwritten.
"""
import sqlite3
import stat
import sys
from contextlib import closing
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
    RUN_EN_COURS = "run_en_cours"


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


def projets_avec_run_ouvert(db_path: Path) -> frozenset[str]:
    """Projects with an unfinished row in `pipeline_runs`; empty if there is no database."""
    if not db_path.is_file():
        return frozenset()
    try:
        with closing(sqlite3.connect(f"{db_path.resolve().as_uri()}?mode=ro", uri=True)) as db:
            lignes = db.execute(
                "SELECT DISTINCT project_id FROM pipeline_runs WHERE finished_at IS NULL"
            ).fetchall()
    except sqlite3.Error:
        _logger.warning("open_runs_unreadable", extra={"db": db_path.name})
        return frozenset()
    return frozenset(str(ligne[0]) for ligne in lignes)


def installer_sur_tous(
    workspace: Path, projets_occupes: frozenset[str] = frozenset()
) -> dict[str, EtatHook]:
    """Install the hook in every project folder of `workspace`; the state of each.

    A project listed in `projets_occupes` has an open run: it is skipped, since a
    hook that changes during a run blocks it (ADR-084).
    """
    if not workspace.is_dir():
        return {}
    return {
        d.name: EtatHook.RUN_EN_COURS if d.name in projets_occupes else installer_hook(d)
        for d in sorted(workspace.iterdir())
        if d.is_dir() and not d.name.startswith(".")
    }


def main(workspace: Path, db_path: Path | None = None) -> int:
    """Print what was done for each project; exit 1 if one was skipped or left alone."""
    occupes = projets_avec_run_ouvert(db_path) if db_path else frozenset()
    resultats = installer_sur_tous(workspace, occupes)
    for nom, etat in resultats.items():
        sys.stdout.write(f"{nom} : {etat.value}" + chr(10))
    if not resultats:
        sys.stdout.write(f"Aucun projet dans {workspace}" + chr(10))
    a_revoir = {EtatHook.DIFFERENT, EtatHook.RUN_EN_COURS}
    return 1 if a_revoir & set(resultats.values()) else 0


if __name__ == "__main__":
    from tessera.config import settings

    sys.exit(main(settings.ide_workspace_dir, settings.ide_db_path))
