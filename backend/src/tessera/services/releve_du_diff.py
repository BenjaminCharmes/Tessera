"""What a run's diff adds: new files, and the added line numbers of each file — ticket-659."""
import re
from dataclasses import dataclass
from pathlib import Path

from tessera.services.numerotation import lire_git, ref_de_base

_EN_TETE_BLOC = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


@dataclass(frozen=True)
class Releve:
    """What the run's diff adds: new files, and added line numbers per file."""

    ajoutes: frozenset[str]
    lignes: dict[str, set[int]]


def releve_du_diff(depot: Path, base: str) -> Releve:
    diff = lire_git(
        depot, "diff", "-U0", "--no-renames", "--relative", "--no-color",
        "--src-prefix=a/", "--dst-prefix=b/", f"{ref_de_base(base)}...HEAD",
    )
    ajoutes: set[str] = set()
    lignes: dict[str, set[int]] = {}
    courant: str | None = None
    nouveau = en_tete = False
    for ligne in diff.splitlines():
        if ligne.startswith("diff --git"):
            courant, nouveau, en_tete = None, False, True
        elif ligne.startswith("@@"):
            en_tete = False
            bloc = _EN_TETE_BLOC.match(ligne)
            if courant is not None and bloc:
                debut, taille = int(bloc.group(1)), int(bloc.group(2) or 1)
                lignes.setdefault(courant, set()).update(range(debut, debut + taille))
        elif en_tete and ligne.startswith("new file mode"):
            nouveau = True
        elif en_tete and ligne.startswith("+++ "):
            cible = ligne[4:].split("\t")[0]
            courant = cible[2:] if cible.startswith("b/") else None
            if courant is not None and nouveau:
                ajoutes.add(courant)
    return Releve(frozenset(ajoutes), lignes)


def lire_lignes(depot: Path, chemin: str, numeros: set[int]) -> list[str]:
    fichier = depot / chemin
    if not fichier.is_file():
        return []
    texte = fichier.read_bytes().decode("utf-8", errors="replace").split("\n")
    return [texte[n - 1] for n in sorted(numeros) if 0 < n <= len(texte)]
