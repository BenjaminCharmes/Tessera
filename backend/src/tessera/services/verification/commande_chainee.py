"""A test command chained with `&&`, split into steps — ticket-337.

Le testeur lance sa commande sans shell. `a && b` y devenait un seul
programme, `a`, qui recevait `&&` et `b` en arguments : `b` ne tournait
jamais, et le testeur annonçait vert ce qu'il n'avait pas lancé. Avec `npm` en
tête, `npm.cmd` passait par cmd.exe, qui enchaînait — par chance, et
seulement sous Windows.

On découpe donc sur `&&` et l'on lance les étapes une à une. Les autres
opérateurs de shell sont refusés plutôt qu'ignorés en silence : un projet qui
en a besoin passe par un script.
"""
import shlex

_ET = "&&"
_NON_GERES = frozenset({"||", "|", ";", "&", ">", ">>", "<", "2>", "2>&1"})


class CommandeNonGeree(ValueError):
    """The command uses a shell construct the testeur cannot run."""


def decouper(commande: str) -> list[list[str]]:
    """Split ``commande`` on ``&&`` into the argument lists of its steps."""
    jetons = shlex.split(commande)
    for jeton in jetons:
        if jeton in _NON_GERES:
            raise CommandeNonGeree(
                f"« {jeton} » n'est pas pris en charge : le testeur lance sa "
                "commande sans shell. Enchaîner avec && ou passer par un script."
            )
    etapes: list[list[str]] = [[]]
    for jeton in jetons:
        if jeton == _ET:
            etapes.append([])
        else:
            etapes[-1].append(jeton)
    if any(not etape for etape in etapes):
        raise CommandeNonGeree(f"Étape vide dans la commande de test : « {commande} ».")
    return etapes
