"""Refus des points de reparse dans l'arbre d'un run — audit du 17/11, constat C2.

Une jonction (`mklink /J`) se crée sans privilège, vers un dossier que le compte
de l'agent ne lit pas ; git, lancé sous le compte de l'utilisateur, la suit :
`git add -A` en indexe la cible et `git diff` la montre. Avant tout ajout, tout
diff ou toute empreinte, l'arbre se parcourt donc **sans entrer dans un lien**.

Un lien que git ignore (`.gitignore`, `.git/info/exclude`) n'entre jamais dans
l'index : c'est le cas des liens posés par `populate` (ADR-056), qui n'en admet
que d'ignorés. Tout autre lien est refusé, nommé, et le run passe `blocked`
(ADR-037).
"""
import asyncio
import os
import stat
from collections.abc import Awaitable, Callable
from pathlib import Path

from tessera.services.git_workspace.erreurs import GitWorkspaceError

#: `stat.FILE_ATTRIBUTE_REPARSE_POINT` n'existe que sous Windows (cf. populate).
_REPARSE_POINT = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))

EstIgnore = Callable[[str], Awaitable[bool]]


class LienNonDeclare(GitWorkspaceError):
    """The run tree holds a link `populate` did not place, git does not ignore."""

    def __init__(self, liens: list[str]) -> None:
        self.liens = liens
        super().__init__(
            "Lien (jonction ou lien symbolique) non déclaré dans l'arbre du run : "
            + ", ".join(liens)
            + ". Rien n'est indexé ; retire-le."
        )


def _est_un_lien(entree: os.DirEntry[str]) -> bool:
    """True for a symlink, a junction or any reparse point, judged on the entry itself."""
    if entree.is_symlink():
        return True
    attributs = int(getattr(entree.stat(follow_symlinks=False), "st_file_attributes", 0))
    return bool(attributs & _REPARSE_POINT)


def trouver_liens(racine: Path) -> list[str]:
    """Every link under `racine`, as `/`-separated paths relative to it.

    The walk never enters a link, and skips `.git`.
    """
    trouves: list[str] = []
    pile = [racine]
    while pile:
        dossier = pile.pop()
        try:
            with os.scandir(dossier) as entrees:
                for entree in entrees:
                    chemin = Path(entree.path)
                    if _est_un_lien(entree):
                        trouves.append(chemin.relative_to(racine).as_posix())
                    elif entree.is_dir(follow_symlinks=False) and entree.name != ".git":
                        pile.append(chemin)
        except OSError:
            continue
    return sorted(trouves)


#: Arguments de `git ls-files` qui rendent l'entrée d'index d'un chemin, pathspec littéral.
def args_entree_d_index(chemin: str) -> tuple[str, ...]:
    return ("ls-files", "-s", "-z", "--", f":(literal){chemin}")


def est_lien_suivi(sortie: str, chemin: str) -> bool:
    """True when the index holds exactly `chemin`, as a symlink (mode 120000).

    A folder that merely contains tracked files does not qualify: a junction
    standing in for it would be followed by git.
    """
    for entree in sortie.split("\0"):
        meta, _, nom = entree.partition("\t")
        if nom == chemin and meta.split(" ")[0] == "120000":
            return True
    return False


async def liens_non_declares(racine: Path, est_admis: EstIgnore) -> list[str]:
    """The links under `racine` that `est_admis` does not accept."""
    liens = await asyncio.to_thread(trouver_liens, racine)
    return [lien for lien in liens if not await est_admis(lien)]


async def refuser_les_liens(racine: Path, est_admis: EstIgnore) -> None:
    """Raise `LienNonDeclare` when the tree holds a link git would follow."""
    refuses = await liens_non_declares(racine, est_admis)
    if refuses:
        raise LienNonDeclare(refuses)
