"""The working folder of a run: a named worktree, outside the project checkout.

ADR-056, ticket-522. Unlike `temporary_worktree.detached_worktree` (detached,
gone when the request ends), this one is checked out on the ticket branch and
outlives the request. It is created from `origin/<base>`, resumed when a run
left it behind clean, and never removed while it holds unsaved work.
"""
import re
from dataclasses import dataclass
from pathlib import Path

from tessera.config import settings
from tessera.services.git_workspace import GitCommandError, GitWorkspaceError
from tessera.services.run_worktree_populate import retirer_les_liens
from tessera.services.temporary_worktree import run_git
from tessera.utils.logger import get_logger
from tessera.utils.project_id import validate_project_id

_logger = get_logger(__name__)


class WorktreeError(GitWorkspaceError):
    """Base class for the errors of a run worktree."""


class CheminRefuse(WorktreeError):
    """An id or a resolved path would put the worktree outside its folder."""


class WorktreeOccupe(WorktreeError):
    """The worktree folder exists but is not a clean checkout of the branch."""


class BrancheDejaExtraite(WorktreeError):
    """Git keeps a branch in one working tree only; another one holds it."""

    def __init__(self, branche: str, ou: Path) -> None:
        super().__init__(
            f"La branche « {branche} » est déjà extraite dans {ou}. "
            "Rien n'est forcé : change de branche à cet endroit, puis relance."
        )
        self.branche = branche
        self.ou = ou


class TravailNonSauve(WorktreeError):
    """The worktree holds changes nobody committed; it is left in place."""

    def __init__(self, racine: Path, etat: str) -> None:
        super().__init__(
            f"Le worktree {racine} porte du travail non commité, il reste en place :\n{etat}"
        )
        self.racine = racine
        self.etat = etat


class LienPersistant(WorktreeError):
    """A link survived `retirer_les_liens`; nothing is deleted (ticket-523)."""

    def __init__(self, racine: Path, liens: list[Path]) -> None:
        noms = ", ".join(str(lien) for lien in liens)
        super().__init__(f"Le worktree {racine} garde des liens, rien n'est effacé : {noms}")
        self.liens = liens


@dataclass(frozen=True)
class RunWorktree:
    """Where a run works: the worktree root, the project inside it, the branch."""

    racine: Path
    projet: Path
    branche: str


_TICKET_ID_RE = re.compile(r"ticket-[0-9]+")


def _sous_le_dossier(racine: Path) -> Path:
    """`racine` resolved, or `CheminRefuse` when it leaves `ide_worktrees_dir`.

    Résolu : un lien symbolique posé dans le dossier des worktrees ne doit pas
    mener une écriture, ou une suppression, ailleurs sur le disque.
    """
    dossier = settings.ide_worktrees_dir.resolve()
    resolue = racine.resolve()
    if resolue == dossier or not resolue.is_relative_to(dossier):
        raise CheminRefuse(f"{racine} n'est pas sous {dossier} : rien n'est écrit ni supprimé.")
    return resolue


def _racine_sure(project_id: str, ticket_id: str) -> Path:
    """The worktree root of a ticket, built only from validated ids."""
    if not validate_project_id(project_id):
        raise CheminRefuse(f"Identifiant de projet refusé : {project_id!r}.")
    if not _TICKET_ID_RE.fullmatch(ticket_id):
        raise CheminRefuse(f"Identifiant de ticket refusé : {ticket_id!r}.")
    return _sous_le_dossier(settings.ide_worktrees_dir / project_id / ticket_id)


async def _extraites(depot: Path) -> dict[str, Path]:
    """Map each branch checked out somewhere in the repository to its folder."""
    sortie = await run_git(depot, "worktree", "list", "--porcelain")
    par_branche: dict[str, Path] = {}
    dossier: Path | None = None
    for ligne in sortie.splitlines():
        if ligne.startswith("worktree "):
            dossier = Path(ligne.removeprefix("worktree "))
        elif ligne.startswith("branch refs/heads/") and dossier is not None:
            par_branche[ligne.removeprefix("branch refs/heads/")] = dossier
    return par_branche


def _meme_dossier(a: Path, b: Path) -> bool:
    return a.resolve() == b.resolve()


async def _etat(racine: Path) -> str:
    return (await run_git(racine, "status", "--porcelain", "--untracked-files=normal")).strip()


async def _projet_dans(racine: Path, depot: Path, project_path: Path) -> Path:
    """The project folder inside the worktree, from its place in the repository."""
    toplevel = Path((await run_git(depot, "rev-parse", "--show-toplevel")).strip())
    try:
        relatif = project_path.resolve().relative_to(toplevel.resolve())
    except ValueError as exc:
        raise WorktreeError(f"{project_path} n'est pas dans le dépôt {toplevel}.") from exc
    return racine / relatif


async def _reprendre(racine: Path, branche: str, extraites: dict[str, Path]) -> None:
    """Accept a leftover folder only if it is this branch's worktree and holds nothing."""
    ici = extraites.get(branche)
    if ici is None or not _meme_dossier(ici, racine):
        raise WorktreeOccupe(f"{racine} existe mais n'est pas le worktree de « {branche} ».")
    if await _etat(racine):
        raise WorktreeOccupe(f"{racine} porte des changements non commités ; il n'est pas repris.")
    _logger.info("run_worktree_resumed", extra={"racine": str(racine), "branche": branche})


async def _ajouter(depot: Path, racine: Path, branche: str, base: str) -> None:
    try:
        await run_git(depot, "rev-parse", "--verify", "--quiet", f"refs/heads/{branche}")
    except GitCommandError:
        await run_git(depot, "worktree", "add", "-b", branche, str(racine), f"origin/{base}")
    else:
        await run_git(depot, "worktree", "add", str(racine), branche)


async def creer(
    depot: Path,
    project_path: Path,
    project_id: str,
    ticket_id: str,
    branche: str,
    base: str,
) -> RunWorktree:
    """Create, or resume, the worktree of `ticket_id` on `branche`, forked from `origin/<base>`.

    The checkout of `depot` is neither read nor moved. Raises `BrancheDejaExtraite`
    when another working tree holds the branch, `WorktreeOccupe` when the folder
    is there but is not a clean worktree of it, `CheminRefuse` when an id is not
    valid or the root would leave `ide_worktrees_dir`. Nothing is ever forced.
    """
    racine = _racine_sure(project_id, ticket_id)
    if branche.startswith("-"):
        raise CheminRefuse(f"Nom de branche refusé : {branche!r}.")
    projet = await _projet_dans(racine, depot, project_path)
    await run_git(depot, "fetch", "origin", base)
    extraites = await _extraites(depot)
    ailleurs = extraites.get(branche)
    if ailleurs is not None and not _meme_dossier(ailleurs, racine):
        raise BrancheDejaExtraite(branche, ailleurs)
    if racine.exists():
        await _reprendre(racine, branche, extraites)
    else:
        await _ajouter(depot, racine, branche, base)
    return RunWorktree(racine=racine, projet=projet, branche=branche)


async def supprimer(wt: RunWorktree, depot: Path) -> None:
    """Remove the worktree, unless it holds unsaved work (`TravailNonSauve`).

    Never `--force` on a dirty tree: what was not committed is what nobody saved.
    A root outside `ide_worktrees_dir` raises `CheminRefuse` before anything is touched.
    The links come off first, before the status and before any removal: a deletion
    must never reach the inside of one. A link that stays raises `LienPersistant`.
    """
    _sous_le_dossier(wt.racine)
    if wt.racine.exists():
        restants = retirer_les_liens(wt.racine)
        if restants:
            raise LienPersistant(wt.racine, restants)
        etat = await _etat(wt.racine)
        if etat:
            raise TravailNonSauve(wt.racine, etat)
        await run_git(depot, "worktree", "remove", str(wt.racine))
    # Efface aussi l'enregistrement d'un worktree dont le dossier a disparu.
    await run_git(depot, "worktree", "prune")
