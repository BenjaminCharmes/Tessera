"""Un diff de run qui touche `memory/supervision.md` — ticket-853, ADR-080.

Même lecteur que `lecons_touchees` : le journal du superviseur est écrit par le
service seul, donc **toute** ligne changée dans un diff de run compte. Ce module
ne juge que le diff ; l'exception d'une intervention du superviseur se décide
par le type du run, dans `pipeline`, jamais par le chemin.
"""
from tessera.services.noyau.diff_changements import lire_diff

_FIN_DE_CHEMIN = "memory/supervision.md"


def lignes_du_journal(diff: str) -> list[str]:
    """The lines `diff` changes in the journal, or a mark for a file touched without a line."""
    touchees: list[str] = []
    for fichier in lire_diff(diff):
        chemin = fichier.chemin
        if chemin != _FIN_DE_CHEMIN and not chemin.endswith("/" + _FIN_DE_CHEMIN):
            continue
        if not fichier.changements:
            touchees.append(f"{chemin} (fichier touché)")
        touchees.extend(
            f"{chemin} : {c.texte.strip() or '(ligne vide)'}" for c in fichier.changements
        )
    return touchees
