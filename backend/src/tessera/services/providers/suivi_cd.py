"""Le dossier courant d'une ligne de shell, tant qu'il se lit avec certitude — ticket-931.

Un `cd`/`pushd` en tête, relatif ou absolu, se suit ; plusieurs se composent.
Ce qui ne se suit pas (variable non définie, `cd -`, `popd`, sous-shell, `cd`
au milieu de la ligne) rend `DOSSIER_INCERTAIN` : une cible relative y est
refusée, faute de savoir à quoi elle est relative.
"""
import posixpath
from pathlib import Path

from tessera.services.providers.developpement_chemin import developper, est_absolu, est_indetermine

#: Préfixe d'une cible relative dont le dossier est inconnu. `$?` ne se
#: développe jamais : `est_indetermine` le refuse.
DOSSIER_INCERTAIN = "$?dossier-incertain"

#: Ce que l'agent lit quand une cible relative suit un changement de dossier opaque.
CD_INCERTAIN_REFUS = (
    "Écriture refusée : le dossier courant change d'une façon que la garde ne "
    "sait pas suivre (variable non définie, `cd -`, `popd`, sous-shell). "
    "Écris la cible avec un chemin absolu."
)

_CHANGEMENTS_DE_DOSSIER = frozenset({"cd", "pushd", "popd"})
_PONCTUATION = frozenset("();<>|&")


def _nom(jeton: str) -> str:
    return Path(jeton.replace("\\", "/")).name.lower().removesuffix(".exe")


def _lisible(dossier: str) -> bool:
    if not dossier or dossier == "-" or dossier.startswith("-"):
        return False
    if all(c in _PONCTUATION for c in dossier) or any(c in dossier for c in "*?"):
        return False
    return not est_indetermine(dossier)


def _composer(courant: str | None, dossier: str) -> str:
    if courant is None or est_absolu(dossier):
        return dossier
    return posixpath.join(courant, dossier)


def dossier_de_tete(jetons: list[str]) -> tuple[str | None, list[str]]:
    """Le dossier courant après les `cd x &&` de tête, et les jetons qui restent.

    `None` : le dossier de départ. `DOSSIER_INCERTAIN` : on ne sait plus où l'on est.
    """
    courant: str | None = None
    reste = jetons
    while len(reste) >= 4 and _nom(reste[0]) in ("cd", "pushd") and reste[2] in ("&&", ";"):
        dossier = developper(reste[1]) if _lisible(developper(reste[1])) else None
        if dossier is None:
            courant = DOSSIER_INCERTAIN
            reste = reste[3:]
            break
        courant = _composer(courant, dossier)
        reste = reste[3:]
    # Un autre changement de dossier plus loin, ou un `cd` de tête mal formé.
    if any(_nom(j) in _CHANGEMENTS_DE_DOSSIER for j in reste):
        return DOSSIER_INCERTAIN, reste
    return courant, reste


def depuis(dossier: str | None, cible: str) -> str:
    """La cible développée, relative au dossier suivi ; absolue, elle reste telle quelle."""
    cible = developper(cible)
    if dossier is None or est_absolu(cible) or est_indetermine(cible):
        return cible
    return f"{dossier}/{cible}"
