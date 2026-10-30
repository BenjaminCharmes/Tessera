"""The single walk up to the repository root — ticket-676.

Six modules used to climb the folder tree looking for a `.git`, each with its
own copy of the loop and of the `git_root` comparison (ADR-028). They now
share this module: one answer to "is this folder a repository" and one
function to find the repository above a project.

A `.git` **file** counts like a `.git` folder: a linked worktree carries one
(ADR-056), and it is a repository root all the same.

Nothing here resolves a path: the caller passes what it wants climbed, resolved
or not.
"""
from pathlib import Path

from tessera.services.manifeste import lire_valeur

#: The only `git_root` value that opens the repository above the project
#: (ADR-028). Any other value disarms nothing.
GIT_ROOT_ANCESTOR = "ancestor"


def est_ancestor(git_root: object | None) -> bool:
    """True when a `git_root` value is exactly `ancestor`."""
    return git_root == GIT_ROOT_ANCESTOR


def declare_ancestor(project_path: Path) -> bool:
    """True when the project's manifest declares `git_root: ancestor`."""
    return est_ancestor(lire_valeur(project_path, "git_root"))


def est_un_depot(dossier: Path) -> bool:
    """True when `dossier` holds a `.git` — a folder, or a file (worktree)."""
    return (dossier / ".git").exists()


def depot_le_plus_proche(depart: Path) -> Path | None:
    """The first folder, `depart` included, that is a repository root."""
    for dossier in (depart, *depart.parents):
        if est_un_depot(dossier):
            return dossier
    return None


def depot_au_dessus(depart: Path) -> Path | None:
    """The first ancestor of `depart` that is a repository root, if any.

    `depart` itself is not looked at: this is the repository that *contains*
    a project, not the one it might own.
    """
    for dossier in depart.parents:
        if est_un_depot(dossier):
            return dossier
    return None


def racine_ecriture_projet(project_path: Path, dans_le_parent: bool) -> Path:
    """The folder a project may write under (ADR-031, ADR-028).

    Its own resolved folder, or — when it works in the repository that holds
    it — that repository, and not the plain parent: `projects/` would be no
    meaningful root. Without any repository above, the plain parent.
    """
    racine = project_path.resolve()
    if not dans_le_parent:
        return racine
    depot = depot_au_dessus(racine)
    return depot if depot is not None else racine.parent
