"""What a test timeout says about its steps — ticket-514.

Un délai dépassé ne dit pas quelle étape de la commande a débordé. Ce module
écrit, en une ligne, les étapes terminées avec leur durée puis l'étape coupée.
"""
import shlex
from pathlib import PurePath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tessera.services.test_runner import TestResult

# Au-delà, le dernier argument est un script en ligne ou un chemin, pas un nom.
_NOM_MAX = 30


def nom_court(commande: str) -> str:
    """Short label of a step: ``pnpm run lint`` -> ``lint``, ``uv run pytest`` -> ``pytest``.

    Falls back to the executable's name when the last argument is an option or
    too long to read in a journal line.
    """
    try:
        mots = shlex.split(commande)
    except ValueError:
        return commande[:_NOM_MAX]
    if not mots:
        return commande
    dernier = mots[-1]
    est_un_nom = not dernier.startswith("-") and " " not in dernier
    if len(mots) > 1 and est_un_nom and len(dernier) <= _NOM_MAX:
        return dernier
    return PurePath(mots[0]).stem[:_NOM_MAX] or mots[0][:_NOM_MAX]


def _secondes(duree_ms: int) -> str:
    return f"{round(duree_ms / 1000)} s"


def detail_du_delai(result: "TestResult") -> str:
    """Finished steps with their duration, then the cut step; empty if no step is known."""
    parties = [f"{nom_court(e.commande)} {_secondes(e.duree_ms)}" for e in result.etapes]
    if result.etape_coupee is not None:
        coupee = result.etape_coupee
        parties.append(
            f"{nom_court(coupee.commande)} coupé après {_secondes(coupee.duree_ms)}"
        )
    return ", ".join(parties)


def ligne_de_delai(result: "TestResult") -> str:
    """The pipeline-log text of a timeout: limit, then the step detail when known."""
    entete = f"délai dépassé ({result.delai_s:.0f} s)"
    detail = detail_du_delai(result)
    return f"{entete} — {detail}" if detail else entete
