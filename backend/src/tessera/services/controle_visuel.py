"""The visual check a project declares — ticket-617, ADR-062.

Pur : ce module lit la déclaration et décide si un diff la déclenche. Il ne
démarre rien et ne capture rien (étape de run : ticket-618). Rien ne se devine :
sans `pipeline.controle_visuel`, sans `interface` ou sans démarrage lisible,
la porte reste fermée.
"""
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from tessera.services.captures_config import ConfigCaptures, parse_captures_config
from tessera.services.manifeste import lire_objet, lire_valeur

MODES: tuple[str, ...] = ("joindre", "relire")
#: Délai de démarrage de l'app, en secondes : défaut et plafond.
DELAI_DEFAUT_S = 120
DELAI_MAX_S = 300
#: Jeton remplacé par un port libre à l'étape de run.
JETON_PORT = "{port}"


@dataclass(frozen=True)
class Demarrage:
    """How to start the app: a command carrying `{port}` and a time limit."""

    commande: str
    delai_s: int = DELAI_DEFAUT_S


@dataclass(frozen=True)
class ControleVisuel:
    """A usable declaration: the mode, the screens and what triggers them."""

    mode: str
    captures: ConfigCaptures
    interface: tuple[str, ...]
    demarrage: Demarrage


def _delai(brut: object) -> int:
    """Read `delai_s` ; unusable falls back to the default, too large is capped."""
    # `bool` est un `int` en Python : `true` ne serait pas un délai.
    if type(brut) is not int or brut <= 0:
        return DELAI_DEFAUT_S
    return min(brut, DELAI_MAX_S)


def _demarrage(brut: object) -> Demarrage | None:
    if not isinstance(brut, dict):
        return None
    commande = brut.get("commande")
    if not isinstance(commande, str) or JETON_PORT not in commande:
        return None
    return Demarrage(commande=commande.strip(), delai_s=_delai(brut.get("delai_s")))


def _interface(brut: object) -> tuple[str, ...]:
    """Read `interface` ; no default, so anything unusable means no trigger."""
    if not isinstance(brut, list):
        return ()
    return tuple(e.strip() for e in brut if isinstance(e, str) and e.strip())


def _controle(mode: object, brut: object) -> ControleVisuel | None:
    if not isinstance(mode, str) or mode not in MODES or not isinstance(brut, dict):
        return None
    captures = parse_captures_config(brut)
    demarrage = _demarrage(brut.get("demarrage"))
    if captures is None or demarrage is None:
        return None
    return ControleVisuel(mode, captures, _interface(brut.get("interface")), demarrage)


def lire_le_controle(project_path: Path) -> ControleVisuel | None:
    """Read the declared visual check, or None when the gate is not open."""
    pipeline = lire_objet(project_path, "pipeline")
    if pipeline is None:
        return None
    return _controle(pipeline.get("controle_visuel"), lire_valeur(project_path, "captures"))


def _declenche(chemin: str, entree: str) -> bool:
    if entree.startswith("."):
        return chemin.endswith(entree)
    return chemin.startswith(entree)


def controle_du(chemins: Iterable[str], config: ControleVisuel) -> bool:
    """True when one path sits under a declared prefix or has a declared extension."""
    return any(
        _declenche(chemin, entree)
        for chemin in chemins
        for entree in config.interface
    )
