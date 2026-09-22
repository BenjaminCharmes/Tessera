"""Les fichiers qu'une ligne de shell écrit, pour les formes simples — ticket-088.

Extrait de `perimetre.py`, qui pose le périmètre ; ici on ne fait que lire une
commande `Bash` et en rendre les cibles. `Bash` est couvert **pour les formes
simples** : `> fichier`, `>> fichier`, `tee fichier`. C'est ce qui attrape une
erreur, pas une frontière contre quelqu'un qui cherche à passer (ADR-031).
"""
import shlex

#: `/dev/null`, `2>&1` : des flux, pas des fichiers du projet.
_NON_FICHIERS = frozenset({"/dev/null", "/dev/stdout", "/dev/stderr"})


def cibles_ecrites(commande: str) -> list[str]:
    """Les fichiers qu'une ligne de shell écrit, pour les formes simples.

    `>`, `>>` et `tee`. La ligne est **tokenisée**, jamais découpée à la main :
    `grep -r 'x > y' src/` ne redirige rien, et une comparaison de caractères
    le prendrait pour une écriture — un faux refus qui priverait l'agent d'une
    commande parfaitement légitime.

    Volontairement incomplet : ce qui ne se lit pas avec certitude n'est pas
    rendu, et passera donc.
    """
    try:
        jetons = shlex.split(commande, posix=True)
    except ValueError:
        # Guillemet non fermé : on ne sait pas lire cette ligne, donc on
        # n'invente pas de cible.
        return []

    cibles: list[str] = []
    for index, jeton in enumerate(jetons):
        suivant = jetons[index + 1] if index + 1 < len(jetons) else None
        cible: str | None = None
        if jeton in (">", ">>"):
            cible = suivant
        elif jeton.startswith(">") and len(jeton) > 1:
            cible = jeton.lstrip(">")
        elif jeton == "tee" and suivant and not suivant.startswith("-"):
            cible = suivant
        if cible and cible not in _NON_FICHIERS and not cible.startswith("&"):
            cibles.append(cible)
    return cibles


__all__ = ["cibles_ecrites"]
