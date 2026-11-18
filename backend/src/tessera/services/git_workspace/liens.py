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
from pathlib import Path

from tessera.services.git_workspace.erreurs import GitWorkspaceError
from tessera.services.noyau.git_commande import build_command

#: `stat.FILE_ATTRIBUTE_REPARSE_POINT` n'existe que sous Windows (cf. populate).
_REPARSE_POINT = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


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


async def _git(racine: Path, args: tuple[str, ...], entree: bytes | None = None) -> tuple[int, str]:
    """Run a read-only git command in `racine`; return its exit code and stdout."""
    proc = await asyncio.create_subprocess_exec(
        *build_command(args),
        cwd=str(racine),
        stdin=asyncio.subprocess.PIPE if entree is not None else asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    sortie, _ = await proc.communicate(entree)
    return proc.returncode or 0, sortie.decode("utf-8", errors="replace")


async def _ignores_en_lot(racine: Path, chemins: list[str]) -> set[str]:
    """The paths of `chemins` git ignores, judged in a single `check-ignore --stdin`.

    Un projet pnpm ou Next porte des milliers de liens, tous ignorés : un appel
    git par lien coûtait des minutes à chaque diff. Un échec fatal du lot
    (code 128) n'admet rien ici ; chaque chemin repasse alors un par un.
    """
    if not chemins:
        return set()
    entree = "".join(f"{chemin}\0" for chemin in chemins).encode("utf-8")
    code, sortie = await _git(racine, ("check-ignore", "-z", "--stdin"), entree)
    if code not in (0, 1):
        return set()
    return {chemin for chemin in sortie.split("\0") if chemin}


async def _admis_un(racine: Path, chemin: str) -> bool:
    """True for a path git ignores, or a symlink the index tracks as such.

    Ignoré, ou lien symbolique que l'index porte comme tel (mode 120000) : git
    le range comme lien, il ne l'ouvre pas. Un dossier suivi remplacé par une
    jonction n'est ni l'un ni l'autre.
    """
    for forme in (chemin, chemin + "/"):
        if (await _git(racine, ("check-ignore", "-q", "--", forme)))[0] == 0:
            return True
    _, sortie = await _git(racine, args_entree_d_index(chemin))
    return est_lien_suivi(sortie, chemin)


async def liens_non_declares(racine: Path) -> list[str]:
    """The links under `racine` git would follow: neither ignored nor tracked as links."""
    liens = await asyncio.to_thread(trouver_liens, racine)
    ignores = await _ignores_en_lot(racine, liens)
    return [lien for lien in liens if lien not in ignores and not await _admis_un(racine, lien)]


async def refuser_les_liens(racine: Path) -> None:
    """Raise `LienNonDeclare` when the tree holds a link git would follow."""
    refuses = await liens_non_declares(racine)
    if refuses:
        raise LienNonDeclare(refuses)
