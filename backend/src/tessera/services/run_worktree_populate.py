"""Populate a run worktree, and unlink it before anything is removed — ticket-523.

ADR-056, spec § 2. `copy` duplicates what the checkout holds; `link` points the
worktree at the checkout's own folder (a junction on Windows, a symlink elsewhere),
and only for what git ignores. A link is read-only for the file tools: the write
hook resolves it, so a write through it leaves the root and is refused.

The reason `retirer_les_liens` exists: a recursive delete that walks into a
junction empties its target. It happened on 14/10, to the `node_modules` of the
checkout. Links come off first, and nothing here ever lists the inside of one.
"""
import os
import shutil
import stat
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from tessera.models.worktree_config import ConfigWorktree, EntreePopulate
from tessera.services.git_workspace import GitCommandError
from tessera.services.temporary_worktree import run_git
from tessera.utils.logger import get_logger

if TYPE_CHECKING:
    from tessera.services.run_worktree import RunWorktree

if sys.platform == "win32":
    import _winapi

_logger = get_logger(__name__)


def _est_un_lien(chemin: Path) -> bool:
    """True for a symlink or a junction, judged on the entry itself, never its target."""
    attributs = int(getattr(os.lstat(chemin), "st_file_attributes", 0))
    return chemin.is_symlink() or bool(attributs & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def _delier(chemin: Path) -> bool:
    """Remove one link without touching what it points at; False if it stays."""
    for retrait in (os.rmdir, os.unlink):
        try:
            retrait(chemin)
        except OSError:
            continue
        return True
    return False


def retirer_les_liens(racine: Path) -> list[Path]:
    """Unlink every junction and symlink under `racine`; return those that remain.

    The walk never enters a link: a link is judged and removed as an entry, so the
    folder it points at is neither listed nor deleted. An empty result means the
    tree holds no link any more and can be removed recursively.
    """
    restants: list[Path] = []
    with os.scandir(racine) as entrees:
        enfants = [Path(entree.path) for entree in entrees]
    for enfant in enfants:
        if _est_un_lien(enfant):
            if not _delier(enfant):
                restants.append(enfant)
        elif enfant.is_dir():
            restants.extend(retirer_les_liens(enfant))
    return restants


async def _est_ignore(depot: Path, chemin: str) -> bool:
    """`git check-ignore -q`: exit 0 only for an ignored path; any failure says no."""
    try:
        await run_git(depot, "check-ignore", "-q", "--", chemin)
    except GitCommandError:
        return False
    return True


def _creer_le_lien(source: Path, cible: Path) -> None:
    cible.parent.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32" and source.is_dir():
        _winapi.CreateJunction(str(source.resolve()), str(cible))
    else:
        os.symlink(source.resolve(), cible, target_is_directory=source.is_dir())


def _copier(source: Path, cible: Path) -> None:
    cible.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        # `symlinks=True` : un lien du checkout se copie en lien, il ne se suit pas.
        shutil.copytree(source, cible, symlinks=True)
    else:
        shutil.copy2(source, cible)


def _refuser(entree: EntreePopulate, raison: str) -> None:
    extra = {"chemin": entree.path, "mode": entree.mode, "raison": raison}
    _logger.warning("worktree_populate_refuse", extra=extra)


async def _appliquer(entree: EntreePopulate, source: Path, cible: Path, depot: Path) -> None:
    # Le contrôle git passe en premier : un chemin suivi existe déjà dans le worktree.
    if entree.mode == "link" and not await _est_ignore(depot, entree.path):
        _refuser(entree, "non_ignore_par_git")
    elif os.path.lexists(cible):
        # Un worktree repris garde ce qu'un run précédent y a laissé.
        _refuser(entree, "cible_existante")
    elif entree.mode == "copy":
        _copier(source, cible)
    else:
        try:
            _creer_le_lien(source, cible)
        except OSError as exc:
            _logger.warning(
                "worktree_populate_lien_impossible",
                extra={"chemin": entree.path, "erreur": str(exc)},
            )


async def peupler(wt: "RunWorktree", depot: Path, config: ConfigWorktree) -> list[str]:
    """Copy or link each declared entry from `depot` into the worktree.

    Returns the declared paths the checkout does not hold, already logged as
    `worktree_populate_manquant`; the other entries are populated regardless.
    A refused entry (not ignored by git, target already there) is logged and skipped.
    """
    racine = wt.racine.resolve()
    absents: list[str] = []
    for entree in config.populate:
        source = depot / entree.path
        cible = wt.racine / entree.path
        if not os.path.lexists(source):
            _logger.warning("worktree_populate_manquant", extra={"chemin": entree.path})
            absents.append(entree.path)
        elif not cible.parent.resolve().is_relative_to(racine):
            _refuser(entree, "hors_du_worktree")
        else:
            await _appliquer(entree, source, cible, depot)
    return absents
