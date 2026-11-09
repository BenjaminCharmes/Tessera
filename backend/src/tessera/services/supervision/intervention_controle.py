"""Les contrôles de chemins d'une intervention — ticket-854, ADR-080.

Deux portes sur la même garde (`refus_de_chemin`, ticket-851) : avant le commit,
où le journal est refusé à l'action elle-même (le service seul l'écrit), et à la
livraison, qui relit le diff de la branche et y admet la ligne de journal du
service.
"""
import posixpath
from collections.abc import Iterable

from tessera.services.livraison.livraison_intervention import ControleDuDiff
from tessera.services.supervision.superviseur_actions import Action, refus_de_chemin

JOURNAL = "memory/supervision.md"


def _est_le_journal(chemin: str) -> bool:
    return posixpath.normpath(chemin.strip().replace("\\", "/")).casefold() == JOURNAL


def refus_avant_commit(modifies: Iterable[str], action: Action) -> str | None:
    """Why the files an action changed are refused, or None: the journal never is the action's."""
    chemins = list(modifies)
    if any(_est_le_journal(chemin) for chemin in chemins):
        return f"{JOURNAL} : seul le service écrit le journal du superviseur"
    return refus_de_chemin(chemins, action)


def controle_du_journal_seul(chemins: list[str]) -> str | None:
    """The check of a branch that only carries the journal line of an « À toi » case."""
    autres = [chemin for chemin in chemins if not _est_le_journal(chemin)]
    if autres:
        return f"{autres[0]} : une branche « À toi » ne porte que {JOURNAL}"
    return None


def controle_de(action: Action) -> ControleDuDiff:
    """The check the delivery applies to the diff of an `action` branch: its paths, plus the journal."""

    def controle(chemins: list[str]) -> str | None:
        return refus_de_chemin([c for c in chemins if not _est_le_journal(c)], action)

    return controle
