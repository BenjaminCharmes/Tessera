"""The blocks a supervisor decision moves or drops — ticket-856, ADR-080.

Pure functions on the text of `memory/lecons.md` or `memory/contraintes.md`: no
model call, no I/O. A *block* is a bullet of `## Proposées` — its `- ` line and
the indented lines that follow. The supervisor never rewrites one: it is moved
whole to another section, or dropped whole. The caller checks the result with
`deplacement_pur` before anything is written.
"""
import hashlib
import re
from dataclasses import dataclass
from typing import Literal

Genre = Literal["lecon", "regle"]

TITRE_PROPOSEES = "proposées"
TITRE_EN_VIGUEUR = "En vigueur"

#: `*(codeur, reviewer)*` seul sur sa ligne : ce qui suit n'est plus universel.
_MARQUEUR_ROLE = re.compile(r"^\*\([^)]+\)\*$")
_HACHE = 8


@dataclass(frozen=True)
class BlocPropose:
    """One proposed block: its stable id and its text, line for line."""

    genre: Genre
    cible: str
    texte: str


def _titre(ligne: str) -> str | None:
    """Casefolded title of a level-2 heading, `None` for any other line."""
    if ligne.startswith("##") and not ligne.startswith("###"):
        return ligne[2:].strip().casefold()
    return None


def cible_de(genre: Genre, texte: str) -> str:
    """A short id that follows the text of a block, not its position in the file."""
    plie = " ".join(texte.split()).encode("utf-8")
    return f"{genre}-{hashlib.sha256(plie).hexdigest()[:_HACHE]}"


def _bornes_proposees(lignes: list[str]) -> tuple[int, int] | None:
    """Line range (heading excluded) of `## Proposées`, `None` when the section is absent."""
    debut: int | None = None
    for index, ligne in enumerate(lignes):
        titre = _titre(ligne)
        if titre is None:
            continue
        if debut is not None:
            return debut, index
        if titre == TITRE_PROPOSEES:
            debut = index + 1
    return None if debut is None else (debut, len(lignes))


def _fin_du_bloc(lignes: list[str], debut: int, limite: int) -> int:
    fin = debut + 1
    while fin < limite and lignes[fin].strip() and lignes[fin][0].isspace():
        fin += 1
    return fin


def _etendues(lignes: list[str]) -> list[tuple[int, int]]:
    """`(début, fin)` of every block of `## Proposées`, `fin` excluded."""
    bornes = _bornes_proposees(lignes)
    if bornes is None:
        return []
    etendues: list[tuple[int, int]] = []
    index, limite = bornes
    while index < limite:
        if lignes[index].startswith("- ") and lignes[index][2:].strip():
            fin = _fin_du_bloc(lignes, index, limite)
            etendues.append((index, fin))
            index = fin
        else:
            index += 1
    return etendues


def blocs_proposes(contenu: str, genre: Genre) -> list[BlocPropose]:
    """The blocks waiting under `## Proposées`, in file order; empty without the section."""
    lignes = contenu.splitlines()
    return [
        BlocPropose(genre, cible_de(genre, "\n".join(lignes[d:f])), "\n".join(lignes[d:f]))
        for d, f in _etendues(lignes)
    ]


def sections_nommees(contenu: str) -> list[str]:
    """The titles of the level-2 sections of a file, `## Proposées` excluded."""
    titres = [ligne[2:].strip() for ligne in contenu.splitlines() if _titre(ligne)]
    return [t for t in titres if t.casefold() != TITRE_PROPOSEES]


def _fin_de_section(lignes: list[str], titre: str) -> tuple[int, int] | None:
    """`(premier index après le titre, index de la section suivante)` for section `titre`."""
    debut: int | None = None
    for index, ligne in enumerate(lignes):
        courant = _titre(ligne)
        if courant is None:
            continue
        if debut is not None:
            return debut, index
        if courant == titre:
            debut = index + 1
    return None if debut is None else (debut, len(lignes))


def _point_d_insertion(lignes: list[str], debut: int, fin: int) -> int:
    """Before the first role marker of the section (the block stays universal), else at its end."""
    for index in range(debut, fin):
        if _MARQUEUR_ROLE.match(lignes[index].strip()):
            while index - 1 > debut and not lignes[index - 1].strip():
                index -= 1
            return index
    while fin > debut and not lignes[fin - 1].strip():
        fin -= 1
    return fin


def _retirer(lignes: list[str], debut: int, fin: int) -> list[str]:
    """`lignes` without the block, and without the blank line it would leave doubled."""
    reste = lignes[:debut] + lignes[fin:]
    if 0 < debut < len(reste) and not reste[debut].strip() and not reste[debut - 1].strip():
        del reste[debut]
    return reste


def _retrouver(lignes: list[str], genre: Genre, cible: str) -> tuple[int, int]:
    for debut, fin in _etendues(lignes):
        if cible_de(genre, "\n".join(lignes[debut:fin])) == cible:
            return debut, fin
    raise ValueError(f"Bloc introuvable sous « Proposées » : {cible}")


def _recomposer(contenu: str, lignes: list[str]) -> str:
    fin_de_ligne = "\r\n" if "\r\n" in contenu else "\n"
    return fin_de_ligne.join(lignes) + (fin_de_ligne if contenu.endswith(("\n", "\r")) else "")


def _utiles(texte: str) -> list[str]:
    return [ligne for ligne in texte.splitlines() if ligne.strip()]


def retrait_pur(avant: str, apres: str, bloc: str) -> bool:
    """Whether `apres` is `avant` with `bloc` dropped and every other non-blank line unchanged."""
    if ("\r\n" in avant) != ("\r\n" in apres):
        return False
    a, b, n = _utiles(avant), _utiles(bloc), len(_utiles(bloc))
    restes = (a[:i] + a[i + n:] for i in range(len(a) - n + 1) if n and a[i:i + n] == b)
    return any(reste == _utiles(apres) for reste in restes)


def deplacer_bloc(contenu: str, genre: Genre, cible: str, vers: str) -> str:
    """`contenu` with block `cible` moved, as is, to the end of section `vers`.

    `ValueError` when the block or the section is not found, or `vers` is
    `## Proposées` itself.
    """
    nom = vers.strip().removeprefix("##").strip().casefold()
    lignes = contenu.splitlines()
    debut, fin = _retrouver(lignes, genre, cible)
    bloc = lignes[debut:fin]
    reste = _retirer(lignes, debut, fin)
    bornes = None if nom in ("", TITRE_PROPOSEES) else _fin_de_section(reste, nom)
    if bornes is None:
        raise ValueError(f"Section d'accueil introuvable : {vers!r}")
    position = _point_d_insertion(reste, *bornes)
    devant_un_marqueur = position < len(reste) and _MARQUEUR_ROLE.match(reste[position].strip())
    reste[position:position] = [*bloc, ""] if devant_un_marqueur else bloc
    return _recomposer(contenu, reste)


def retirer_bloc(contenu: str, genre: Genre, cible: str) -> str:
    """`contenu` without block `cible`; `ValueError` when it is not under `## Proposées`."""
    lignes = contenu.splitlines()
    debut, fin = _retrouver(lignes, genre, cible)
    return _recomposer(contenu, _retirer(lignes, debut, fin))
