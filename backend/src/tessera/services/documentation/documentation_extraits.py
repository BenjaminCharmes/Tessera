"""Excerpts of a target file attached to a refused edition, for the corrective round."""
from difflib import SequenceMatcher

#: Below this similarity, a passage is not "close" to the missing anchor.
SEUIL_RESSEMBLANCE = 0.6

#: Lines of context kept around each occurrence of an ambiguous anchor.
CONTEXTE = 2


def _numeroter(lignes: list[str], debut: int, fin: int) -> str:
    """Lines ``debut``..``fin`` (0-based, end excluded), numbered from 1."""
    return "\n".join(f"{i + 1}: {lignes[i]}" for i in range(debut, fin))


def passage_proche(avant: str, ancien: str) -> str:
    """Return the passage of ``avant`` closest to ``ancien``, or an empty string.

    Windows have as many lines as ``ancien``; the best one by ``difflib`` ratio
    wins, provided it exceeds ``SEUIL_RESSEMBLANCE``.
    """
    lignes = avant.splitlines()
    taille = max(1, len(ancien.splitlines()))
    if not ancien.strip() or len(lignes) < taille:
        return ""
    meilleur, debut_meilleur = 0.0, -1
    comparateur = SequenceMatcher(autojunk=False)
    comparateur.set_seq2(ancien)
    for debut in range(len(lignes) - taille + 1):
        comparateur.set_seq1("\n".join(lignes[debut : debut + taille]))
        if comparateur.real_quick_ratio() <= meilleur or comparateur.quick_ratio() <= meilleur:
            continue
        ratio = comparateur.ratio()
        if ratio > meilleur:
            meilleur, debut_meilleur = ratio, debut
    if debut_meilleur < 0 or meilleur < SEUIL_RESSEMBLANCE:
        return ""
    return _numeroter(lignes, debut_meilleur, debut_meilleur + taille)


def occurrences_avec_contexte(avant: str, positions: list[int]) -> str:
    """Return each occurrence (given by start offsets) with its surrounding lines."""
    lignes = avant.splitlines()
    blocs: list[str] = []
    for rang, position in enumerate(positions, start=1):
        ligne = avant.count("\n", 0, position)
        debut = max(0, ligne - CONTEXTE)
        fin = min(len(lignes), ligne + CONTEXTE + 1)
        blocs.append(f"Occurrence {rang} :\n{_numeroter(lignes, debut, fin)}")
    return "\n\n".join(blocs)
