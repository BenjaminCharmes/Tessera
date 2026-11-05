"""Lecture d'un diff git unifié : où chaque fichier a changé — ticket-490.

Le seul besoin est de savoir, pour chaque fichier, à quelles lignes du fichier
**résultant** une ligne a été ajoutée ou retirée. Le reste (contenu, contexte)
ne sert pas : l'appelant relit le fichier sur le disque pour savoir dans quelle
section tombe un changement.
"""
import re
from dataclasses import dataclass, field

_ENTETE_FICHIER = re.compile(r"^diff --git a/(?P<ancien>.+?) b/(?P<nouveau>.+)$")
_ENTETE_BLOC = re.compile(r"^@@ -\d+(?:,\d+)? \+(?P<debut>\d+)(?:,\d+)? @@")


@dataclass(frozen=True)
class Changement:
    """One added or removed line.

    `limite` is the number of lines of the resulting file that precede the
    change (the line itself included for an addition, excluded for a removal):
    the section a change belongs to is the last header found within them.
    """

    limite: int
    ajoute: bool
    texte: str


@dataclass
class FichierModifie:
    """A file touched by the diff and the lines that changed in it."""

    chemin: str
    changements: list[Changement] = field(default_factory=list)


def lire_diff(diff: str) -> list[FichierModifie]:
    """Parse a unified git diff into the files it touches, in diff order."""
    fichiers: list[FichierModifie] = []
    courant: FichierModifie | None = None
    # None tant qu'aucun bloc `@@` n'a commencé : les lignes `---` et `+++` de
    # l'en-tête d'un fichier ne sont pas des changements.
    pointeur: int | None = None
    for ligne in diff.splitlines():
        entete = _ENTETE_FICHIER.match(ligne)
        if entete:
            courant = FichierModifie(chemin=entete.group("nouveau"))
            fichiers.append(courant)
            pointeur = None
            continue
        bloc = _ENTETE_BLOC.match(ligne)
        if bloc:
            pointeur = int(bloc.group("debut"))
        elif courant is not None and pointeur is not None and ligne[:1] in (" ", "+", "-"):
            pointeur = _avancer(courant, ligne, pointeur)
    return fichiers


def _avancer(fichier: FichierModifie, ligne: str, pointeur: int) -> int:
    """Record the line if it is a change, and return the next pointer."""
    marque, texte = ligne[0], ligne[1:]
    if marque == "+":
        fichier.changements.append(Changement(pointeur, True, texte))
        return pointeur + 1
    if marque == "-":
        fichier.changements.append(Changement(pointeur - 1, False, texte))
        return pointeur
    return pointeur + 1
