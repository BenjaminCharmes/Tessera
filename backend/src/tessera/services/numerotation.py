"""Numéros de ticket et d'ADR déjà pris — ticket-659.

Un numéro est pris dès qu'il existe quelque part : dans l'arbre de travail,
sur `origin/<base>` ou sur une branche `origin/ticket-*` encore ouverte. Un
agent qui ne lit que son arbre prend le même numéro qu'une autre branche partie
du même `develop`.

Ce module n'importe que la bibliothèque standard : `scripts/prochain_numero.py`
le charge sans environnement Python du backend. Chaque lecture de git est un
appel synchrone ; l'appelant asynchrone passe par `asyncio.to_thread`.
"""
import re
import subprocess
from collections import Counter
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Literal

Genre = Literal["ticket", "adr"]

BASE_PAR_DEFAUT = "develop"
FICHIERS_ADR: tuple[str, ...] = ("memory/decisions.md", "memory/decisions-archive.md")

_NOM_TICKET = re.compile(r"^ticket-(\d+)")
_TITRE_ADR = re.compile(r"^#{2,3}[ \t]+ADR-(\d+).*$", re.MULTILINE)


class GitIllisible(Exception):
    """A git read failed: the numbers it would have given are unknown."""


def lire_git(depot: Path, *args: str) -> str:
    """Stdout of `git <args>` run in `depot`; raises GitIllisible on failure."""
    proc = subprocess.run(
        ["git", "-c", "core.quotePath=false", *args],
        cwd=depot, capture_output=True, check=False,
    )
    if proc.returncode != 0:
        erreur = proc.stderr.decode("utf-8", errors="replace").strip()
        raise GitIllisible(f"git {' '.join(args[:2])} : {erreur}")
    return proc.stdout.decode("utf-8", errors="replace")


def ref_de_base(base: str) -> str:
    """The remote-tracking ref of the base branch."""
    return f"refs/remotes/origin/{base}"


def numeros_de_noms(chemins: Iterable[str]) -> set[int]:
    """Ticket numbers carried by the file names in `chemins`."""
    trouves: set[int] = set()
    for chemin in chemins:
        correspondance = _NOM_TICKET.match(chemin.replace("\\", "/").rsplit("/", 1)[-1])
        if correspondance:
            trouves.add(int(correspondance.group(1)))
    return trouves


def titres_d_adr(texte: str) -> dict[int, str]:
    """The heading line of each ADR in `texte`, by number."""
    return {
        int(m.group(1)): m.group(0).strip() for m in _TITRE_ADR.finditer(texte)
    }


def _pris_dans_l_arbre(depot: Path, genre: Genre) -> set[int]:
    if genre == "ticket":
        return numeros_de_noms(p.name for p in (depot / "tickets").rglob("*.md"))
    pris: set[int] = set()
    for fichier in FICHIERS_ADR:
        chemin = depot / fichier
        if chemin.is_file():
            texte = chemin.read_text(encoding="utf-8", errors="replace")
            pris |= set(titres_d_adr(texte))
    return pris


def noms_de_tickets_sur_la_base(depot: Path, base: str) -> set[str]:
    """File names of every ticket on `origin/<base>`, whatever their folder."""
    liste = lire_git(
        depot, "ls-tree", "-r", "--name-only", ref_de_base(base), "--", "tickets/"
    )
    return {ligne.rsplit("/", 1)[-1] for ligne in liste.splitlines() if ligne.strip()}


def titres_d_adr_sur_la_base(depot: Path, base: str) -> dict[int, str]:
    """The heading line of each ADR on `origin/<base>`, decisions and archive."""
    titres: dict[int, str] = {}
    for fichier in FICHIERS_ADR:
        try:
            titres.update(titres_d_adr(lire_git(depot, "show", f"{ref_de_base(base)}:./{fichier}")))
        except GitIllisible:
            continue  # un dépôt sans archive n'a pas de numéro à y lire
    return titres


def nombre_de_titres_d_adr(texte: str) -> Counter[int]:
    """How many headings carry each ADR number in `texte`."""
    return Counter(int(m.group(1)) for m in _TITRE_ADR.finditer(texte))


def _compter_titres(lire: Callable[[str], str | None]) -> Counter[int]:
    total: Counter[int] = Counter()
    for fichier in FICHIERS_ADR:
        texte = lire(fichier)
        if texte is not None:
            total += nombre_de_titres_d_adr(texte)
    return total


def nombre_de_titres_dans_l_arbre(depot: Path) -> Counter[int]:
    """ADR headings per number in the working tree, decisions and archive together."""
    def lire(fichier: str) -> str | None:
        chemin = depot / fichier
        if not chemin.is_file():
            return None
        return chemin.read_text(encoding="utf-8", errors="replace")

    return _compter_titres(lire)


def nombre_de_titres_au_merge_base(depot: Path, base: str) -> Counter[int]:
    """ADR headings per number where the run left `origin/<base>`.

    Le point de départ du run, pas la tête de la base : un titre qui n'y était
    pas et que le run porte est ajouté par le run, même si la base l'a aussi
    reçu depuis. Lève GitIllisible si le merge-base est introuvable.
    """
    sha = lire_git(depot, "merge-base", ref_de_base(base), "HEAD").strip()

    def lire(fichier: str) -> str | None:
        try:
            return lire_git(depot, "show", f"{sha}:./{fichier}")
        except GitIllisible:
            return None  # un dépôt sans archive n'a pas de numéro à y lire

    return _compter_titres(lire)


def _pris_sur_la_base(depot: Path, genre: Genre, base: str) -> set[int]:
    if genre == "ticket":
        return numeros_de_noms(noms_de_tickets_sur_la_base(depot, base))
    return set(titres_d_adr_sur_la_base(depot, base))


def _pris_sur_les_branches(depot: Path, genre: Genre, base: str) -> set[int]:
    """Numbers added on `origin/ticket-*` branches and absent from the base."""
    selection = ["--remotes=origin/ticket-*", f"^{ref_de_base(base)}"]
    if genre == "adr":
        diff = lire_git(depot, "log", *selection, "-p", "-U0", "--format=", "--", *FICHIERS_ADR)
        lignes_ajoutees = [ligne[1:] for ligne in diff.splitlines() if ligne.startswith("+")]
        return set(titres_d_adr("\n".join(lignes_ajoutees)))
    noms = lire_git(
        depot, "log", *selection, "--diff-filter=A", "--name-only", "--format=", "--", "tickets/"
    )
    branches = lire_git(
        depot, "for-each-ref", "--format=%(refname:lstrip=3)", "refs/remotes/origin/ticket-*"
    )
    return numeros_de_noms(noms.splitlines()) | numeros_de_noms(branches.splitlines())


def numeros_pris(
    depot: Path, genre: Genre, base: str = BASE_PAR_DEFAUT, *, strict: bool = False
) -> set[int]:
    """Every number of `genre` taken on the tree, on `origin/<base>` or on a branch.

    Without `strict`, a source git cannot read (no remote yet) is skipped: the
    script advises. With it, the first unreadable source raises GitIllisible,
    so that the delivery step fails closed (ADR-039).
    """
    sources: tuple[Callable[[], set[int]], ...] = (
        lambda: _pris_dans_l_arbre(depot, genre),
        lambda: _pris_sur_la_base(depot, genre, base),
        lambda: _pris_sur_les_branches(depot, genre, base),
    )
    pris: set[int] = set()
    for lire in sources:
        try:
            pris |= lire()
        except GitIllisible:
            if strict:
                raise
    return pris


def prochain_numero(depot: Path, genre: Genre, base: str = BASE_PAR_DEFAUT) -> int:
    """The largest number taken plus one."""
    return max(numeros_pris(depot, genre, base), default=0) + 1
