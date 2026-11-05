"""Un diff de run qui touche `memory/lecons.md` — ticket-804, ADR-074.

Seul le service écrit ce fichier, après le tour du codeur. Une ligne qu'un
codeur y ajoute, retire, ou déplace sous `## En vigueur` changerait la
consigne de tous les agents suivants sans relecture : contrairement à
`contraintes.md`, **aucune** ligne n'est admise à ce tour, pas même sous
`## Proposées`. Le diff est analysé comme celui de `contraintes_touchees`,
par le même lecteur ; le fichier n'a pas besoin d'être relu sur le disque,
puisque toute modification compte.
"""
from tessera.services.diff_changements import lire_diff

_FIN_DE_CHEMIN = "memory/lecons.md"


def lignes_de_lecons(diff: str) -> list[str]:
    """The lines `diff` changes in lecons.md, or a mark for a file touched without a line."""
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
