"""The environment of every process that runs a project's code — ticket-888.

Les tests, les services, l'app du contrôle visuel et les captures exécutent du
code qu'un agent a écrit. Hérité tel quel, l'environnement du backend leur
donnerait les secrets de Tessera et les jetons GitHub, que `env_du_sous_processus`
retire déjà aux agents (ticket-873). Les commandes `git` du backend ne passent
pas par ici : le push de la livraison a besoin du jeton.
"""
import os
from collections.abc import Mapping

from tessera.coffre import NOMS_SECRETS

_JETONS_GITHUB: tuple[str, ...] = ("GITHUB_TOKEN", "GH_TOKEN")

# Comparés en minuscules : sous Windows les noms d'environnement ne distinguent
# pas la casse, et une copie en `github_token` porterait le même jeton.
_NOMS_RETIRES = frozenset(nom.lower() for nom in (*NOMS_SECRETS, *_JETONS_GITHUB))


def env_du_code_de_projet(extra: Mapping[str, str] | None = None) -> dict[str, str]:
    """Return a copy of ``os.environ`` without Tessera's secrets, then ``extra``.

    Every name of ``NOMS_SECRETS`` plus ``GITHUB_TOKEN`` and ``GH_TOKEN`` is
    removed ; ``extra`` is applied on top, so a project may still declare a
    variable of its own.
    """
    env = {nom: valeur for nom, valeur in os.environ.items() if nom.lower() not in _NOMS_RETIRES}
    if extra:
        env.update(extra)
    return env
