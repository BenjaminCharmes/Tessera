"""Découper un diff unifié par fichier, et le borner — ticket-540.

Sert la matière de code de la documentation (`documentation_code.py`). Un
fichier du diff est gardé entier ou nommé comme non montré : un hunk coupé en
deux ferait citer à l'agent une moitié de phrase.
"""
import re
from dataclasses import dataclass

from tessera.services.git_workspace import _is_lockfile, _resumer_lockfiles

#: Au-delà de ce nombre de noms, le marqueur de troncature abrège.
_NOMS_MAX = 50

_ENTETE = "diff --git "
_CHEMIN_RE = re.compile(r"^diff --git a/.+ b/(.+)$")


@dataclass(frozen=True)
class Section:
    """Un fichier du diff : son chemin, son texte, ses lignes changées."""

    chemin: str
    texte: str
    lignes: int
    #: Faux pour un fichier supprimé, binaire ou lockfile : pas de contenu à fournir.
    lisible: bool


def _chemin(entete: list[str], premiere: str) -> str:
    for ligne in entete:
        if ligne.startswith("+++ b/"):
            return ligne[6:]
    for ligne in entete:
        if ligne.startswith("rename to "):
            return ligne[10:]
    correspondance = _CHEMIN_RE.match(premiere)
    return correspondance.group(1) if correspondance else ""


def lire_section(brut: str) -> Section:
    """Analyse un bloc `diff --git`. Un lockfile se réduit à une ligne."""
    lignes = brut.splitlines()
    entete: list[str] = []
    for ligne in lignes:
        if ligne.startswith("@@"):
            break
        entete.append(ligne)
    chemin = _chemin(entete, lignes[0])
    changees = sum(1 for ligne in lignes[len(entete):] if ligne[:1] in ("+", "-"))
    inexploitable = any(
        ligne.startswith(("deleted file mode", "Binary files", "GIT binary patch"))
        for ligne in entete
    )
    lockfile = _is_lockfile(chemin)
    texte = _resumer_lockfiles(brut) if lockfile else brut
    return Section(
        chemin, texte if texte.endswith("\n") else texte + "\n", changees,
        lisible=not (inexploitable or lockfile),
    )


def decouper(diff: str) -> list[Section]:
    """Les fichiers d'un diff, dans l'ordre ; vide si le diff l'est."""
    blocs: list[list[str]] = []
    for ligne in diff.splitlines(keepends=True):
        if ligne.startswith(_ENTETE):
            blocs.append([])
        if blocs:
            blocs[-1].append(ligne)
    return [lire_section("".join(bloc)) for bloc in blocs]


def marqueur(noms: list[str]) -> str:
    """La ligne qui dit ce qui n'est pas montré."""
    montres = ", ".join(noms[:_NOMS_MAX]) + ("…" if len(noms) > _NOMS_MAX else "")
    return f"[diff tronqué : {len(noms)} fichiers non montrés : {montres}]\n"


def borner(sections: list[Section], budget: int) -> tuple[str, list[str]]:
    """Les sections qui tiennent dans `budget`, entières, et les noms des autres."""
    gardees: list[str] = []
    non_montres: list[str] = []
    reste = budget
    for section in sections:
        if len(section.texte) <= reste:
            gardees.append(section.texte)
            reste -= len(section.texte)
        else:
            non_montres.append(section.chemin)
    return "".join(gardees), non_montres
