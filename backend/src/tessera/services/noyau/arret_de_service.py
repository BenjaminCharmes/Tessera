"""Small helpers for stopping a service process (ticket-744)."""
from typing import Any


def terminate_if_alive(processus: Any) -> None:
    """Call `terminate()`, treating an already-gone process as stopped.

    `tuer_l_arbre` a déjà emporté le processus : `ProcessLookupError` veut
    dire « arrêté », il ne reste qu'à attendre sa fin.
    """
    try:
        processus.terminate()
    except ProcessLookupError:
        pass


def describe_error(exc: Exception) -> str:
    """The exception type, then its message when it has one.

    `ProcessLookupError()` a un texte vide : sans le type, le journal ne
    disait rien de la cause.
    """
    nom = type(exc).__name__
    return f"{nom}: {exc}" if str(exc) else nom
