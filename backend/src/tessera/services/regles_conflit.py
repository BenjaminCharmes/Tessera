"""Deterministic answers to the trivial conflicts a delivery rebase meets.

A conflict block has three versions: the ancestor (``base``), the branch the
ticket is replayed on (``nôtre``, upstream) and the ticket's own commit
(``leur``). Four rules settle the blocks where nothing is really edited on
both sides, in a fixed order. Everything here is a pure function over text;
the git plumbing stays in ``git_workspace``.
"""
import re
from dataclasses import dataclass

REGLE_IDENTIQUES = "identiques"
REGLE_ESPACEMENT = "espacement"
REGLE_COTE_UNIQUE = "cote-unique"
REGLE_IMPORTS = "imports"

_PYTHON_IMPORT = re.compile(
    r"^(?:import\s+[\w.]+(?:\s+as\s+\w+)?(?:\s*,\s*[\w.]+(?:\s+as\s+\w+)?)*"
    r"|from\s+\.*[\w.]*\s+import\s+(?:\*"
    r"|\w+(?:\s+as\s+\w+)?(?:\s*,\s*\w+(?:\s+as\s+\w+)?)*"
    r"|\([^()]*\)))\s*(?:#.*)?$"
)
_TS_IMPORT = re.compile(
    r"""^import\s+(?:type\s+)?(?:[^'"]+?\s+from\s+)?(?:'[^']*'|"[^"]*")\s*;?\s*$"""
)


@dataclass(frozen=True)
class Resolution:
    """The text that replaces a conflict block, and the rule that produced it."""

    texte: str
    regle: str


def _sans_fin_de_ligne(ligne: str) -> str:
    return ligne.rstrip("\r\n")


def _normaliser_espacement(texte: str) -> list[str]:
    """Lines without trailing whitespace or line ending; indentation is kept."""
    return [_sans_fin_de_ligne(ligne).rstrip() for ligne in texte.splitlines()]


def _est_import(ligne: str) -> bool:
    nue = _sans_fin_de_ligne(ligne).rstrip()
    return bool(_PYTHON_IMPORT.match(nue) or _TS_IMPORT.match(nue))


def _union_imports(base: str, notre: str, leur: str) -> str | None:
    """Both sides only add import lines to the base: keep upstream, then ours."""
    versions = [texte.splitlines(keepends=True) for texte in (base, notre, leur)]
    if not all(_est_import(ligne) for lignes in versions for ligne in lignes):
        return None
    cles_base, cles_notre, cles_leur = (
        [_sans_fin_de_ligne(ligne).rstrip() for ligne in lignes] for lignes in versions
    )
    # Une ligne de la base absente d'un côté est une suppression : on ne la ressuscite pas.
    if not set(cles_base) <= set(cles_notre) or not set(cles_base) <= set(cles_leur):
        return None
    fin = "\r\n" if notre.endswith("\r\n") or "\r\n" in notre else "\n"
    gardees = list(dict.fromkeys(cles_notre))
    gardees += [c for c in dict.fromkeys(cles_leur) if c not in gardees]
    return "".join(ligne + fin for ligne in gardees)


def resoudre_bloc(base: str, notre: str, leur: str) -> Resolution | None:
    """Settle one conflict block by rule, or ``None`` when no rule applies.

    Rules, in order: identical sides; sides that differ by trailing
    whitespace or line endings only; a single side changed from the base;
    import lines added on both sides.
    """
    if notre == leur:
        return Resolution(notre, REGLE_IDENTIQUES)
    if _normaliser_espacement(notre) == _normaliser_espacement(leur):
        return Resolution(notre, REGLE_ESPACEMENT)
    if notre == base:
        return Resolution(leur, REGLE_COTE_UNIQUE)
    if leur == base:
        return Resolution(notre, REGLE_COTE_UNIQUE)
    union = _union_imports(base, notre, leur)
    if union is not None:
        return Resolution(union, REGLE_IMPORTS)
    return None


_DEBUT = "<<<<<<<"
_ANCETRE = "|||||||"
_MILIEU = "======="
_FIN = ">>>>>>>"


def _est_marqueur(ligne: str, marqueur: str) -> bool:
    nue = _sans_fin_de_ligne(ligne)
    return nue == marqueur or nue.startswith(marqueur + " ")


def _lire_bloc(lignes: list[str], debut: int) -> tuple[tuple[str, str, str], int] | None:
    """Reads the diff3 block opened at ``debut``; returns it and the index after it."""
    sections: list[list[str]] = [[], [], []]
    attendus = (_ANCETRE, _MILIEU, _FIN)
    courante = 0
    for i in range(debut + 1, len(lignes)):
        if _est_marqueur(lignes[i], attendus[courante]):
            if courante == len(attendus) - 1:
                notre, base, leur = ("".join(s) for s in sections)
                return (base, notre, leur), i + 1
            courante += 1
        else:
            sections[courante].append(lignes[i])
    return None


def resoudre_fichier(texte: str) -> tuple[str, tuple[str, ...]] | None:
    """Settle every block of a file marked in diff3 style, or return ``None``.

    One block without a rule leaves the whole file to the resolver agent, as
    does a file with no block at all or markers that do not close. Rules come
    back once each, in the order they first applied.
    """
    lignes = texte.splitlines(keepends=True)
    sortie: list[str] = []
    regles: list[str] = []
    i = 0
    while i < len(lignes):
        if not _est_marqueur(lignes[i], _DEBUT):
            sortie.append(lignes[i])
            i += 1
            continue
        lu = _lire_bloc(lignes, i)
        if lu is None:
            return None
        (base, notre, leur), i = lu
        resolution = resoudre_bloc(base, notre, leur)
        if resolution is None:
            return None
        sortie.append(resolution.texte)
        if resolution.regle not in regles:
            regles.append(resolution.regle)
    if not regles:
        return None
    return "".join(sortie), tuple(regles)
