"""Recovers the run worktrees a backend stop left behind — ticket-520.

ADR-056, ADR-018, ADR-037. A run that works in a worktree leaves the checkout of
its project untouched, so a stop costs no branch change there. What it leaves is a
folder under `<worktrees_dir>/<project>/<ticket>`, possibly holding work nobody
committed. At startup the `RunRegistry` is empty: no such folder has a live run.

For each one: unlink first (a recursive delete must never reach the inside of a
link), commit what is dirty as unapproved work, then remove it. A commit that fails
leaves the folder where it is. A folder no known repository registers is logged and
left. A registration whose folder is gone is pruned. Nothing here stops the startup.
"""
import os
import re
from pathlib import Path

from tessera.services.git_workspace import GitWorkspaceError
from tessera.services.pipeline_text import _unapproved_commit_message
from tessera.services.reprise_orphelin import _RAISON_ARRET
from tessera.services.run_worktree import RunWorktree, supprimer
from tessera.services.run_worktree_populate import retirer_les_liens
from tessera.services.temporary_worktree import run_git
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

_TICKET_ID_RE = re.compile(r"ticket-[0-9]+")


def _cle(chemin: Path) -> str:
    """A path in a form comparable with what git prints (case, separators)."""
    return os.path.normcase(str(chemin.resolve()))


async def _depot_de(projet: Path) -> Path | None:
    """The repository root of a project folder, or None when it is not in one."""
    try:
        sortie = await run_git(projet, "rev-parse", "--show-toplevel")
    except (GitWorkspaceError, OSError):
        return None
    return Path(sortie.strip())


async def _depots_connus(workspace_dir: Path) -> list[Path]:
    """The distinct repositories of the projects under `workspace_dir`."""
    if not workspace_dir.is_dir():
        return []
    depots: dict[str, Path] = {}
    for projet in sorted(workspace_dir.iterdir()):
        depot = await _depot_de(projet) if projet.is_dir() else None
        if depot is not None:
            depots.setdefault(_cle(depot), depot)
    return list(depots.values())


async def _enregistres(depot: Path) -> set[str]:
    """Folders a repository registers as worktrees, after pruning the vanished ones."""
    await run_git(depot, "worktree", "prune")
    sortie = await run_git(depot, "worktree", "list", "--porcelain")
    return {
        _cle(Path(ligne.removeprefix("worktree ")))
        for ligne in sortie.splitlines()
        if ligne.startswith("worktree ")
    }


async def _enregistrements(workspace_dir: Path) -> dict[str, Path]:
    """Map each registered worktree folder to the repository that registers it."""
    par_dossier: dict[str, Path] = {}
    for depot in await _depots_connus(workspace_dir):
        try:
            dossiers = await _enregistres(depot)
        except GitWorkspaceError as exc:
            _logger.warning(
                "reprise_worktrees_depot_illisible",
                extra={"depot": str(depot), "error": str(exc)},
            )
            continue
        for dossier in dossiers:
            par_dossier.setdefault(dossier, depot)
    return par_dossier


def _laisser(racine: Path, raison: str, erreur: str = "") -> None:
    extra = {"racine": str(racine), "raison": raison, "error": erreur}
    _logger.warning("reprise_worktree_laisse", extra=extra)


async def _commiter_le_travail(racine: Path, ticket_id: str) -> bool:
    """Commit what the worktree holds as unapproved work; False when it cannot be saved."""
    etat = await run_git(racine, "status", "--porcelain", "--untracked-files=normal")
    if not etat.strip():
        return True
    branche = (await run_git(racine, "branch", "--show-current")).strip()
    if not branche:
        _laisser(racine, "tete_detachee")
        return False
    # Les liens sont déjà retirés : `add --all` ne suit que ce que git ne ignore pas.
    await run_git(racine, "add", "--all", "--", ":/")
    await run_git(racine, "commit", "-m", _unapproved_commit_message(ticket_id, _RAISON_ARRET))
    _logger.info("reprise_worktree_commit", extra={"racine": str(racine), "branche": branche})
    return True


async def _reprendre_un(racine: Path, ticket_id: str, depot: Path) -> None:
    """Save then remove one worktree; every failure leaves the folder in place."""
    try:
        restants = retirer_les_liens(racine)
        if restants:
            _laisser(racine, "liens_persistants", ", ".join(str(r) for r in restants))
            return
        if not await _commiter_le_travail(racine, ticket_id):
            return
        await supprimer(RunWorktree(racine=racine, projet=racine, branche=""), depot)
    except (GitWorkspaceError, OSError) as exc:
        _laisser(racine, "echec", str(exc))
        return
    _logger.info("reprise_worktree_supprime", extra={"racine": str(racine)})


def _candidats(worktrees_dir: Path) -> list[tuple[Path, str]]:
    """Every `<project>/<ticket>` folder under `worktrees_dir`, with its ticket id."""
    if not worktrees_dir.is_dir():
        return []
    trouves: list[tuple[Path, str]] = []
    for projet in sorted(worktrees_dir.iterdir()):
        if projet.is_dir() and not projet.is_symlink():
            trouves.extend(
                (dossier, dossier.name)
                for dossier in sorted(projet.iterdir())
                if dossier.is_dir() and not dossier.is_symlink()
            )
    return trouves


async def _reprendre_tous(workspace_dir: Path, worktrees_dir: Path) -> None:
    registre = await _enregistrements(workspace_dir)
    for racine, ticket_id in _candidats(worktrees_dir):
        depot = registre.get(_cle(racine))
        if depot is None or not _TICKET_ID_RE.fullmatch(ticket_id):
            _laisser(racine, "inconnu_des_depots")
        else:
            await _reprendre_un(racine, ticket_id, depot)


async def reprendre_worktrees_orphelins(workspace_dir: Path, worktrees_dir: Path) -> None:
    """Commit, then remove, the run worktrees a stop left behind; prune dead ones.

    Called by the lifespan right after `reprendre_depots_orphelins`. The checkout of
    a project is never read or moved. Any error is logged and never raised.
    """
    try:
        await _reprendre_tous(workspace_dir, worktrees_dir)
    except Exception:  # noqa: BLE001 — la reprise est un filet, pas une condition
        _logger.exception("reprise_worktrees_echec")
