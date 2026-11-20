"""Le refus qui a terminé le run précédent d'un ticket — ticket-528.

Une branche reprise après un refus d'une porte (audit sécurité, reviewer,
validateur) porte un travail qui n'a pas été jugé bon : le renvoyer tel quel
aux mêmes portes le ferait refuser de nouveau. Le journal du pipeline garde la
fin de chaque run ; on y relit la dernière, sans toucher à la base.
"""
from dataclasses import dataclass
from pathlib import Path

#: Les lignes qui closent un run sans refus de porte : un travail approuvé,
#: ou une coupure (arrêt, quota, budget, délai de tests).
_FINS_SANS_REFUS = ("APPROVED", "BLOCKED", "ARRÊTÉ", "INTERROMPU", "quota épuisé", "budget")


@dataclass(frozen=True)
class Refus:
    """Une porte qui a refusé le run précédent, et ce qu'elle en a dit."""

    porte: str
    motif: str


def _est_debut_de_run(message: str) -> bool:
    """La ligne ``branche <nom>`` ouvre un run ; ``branche reprise (…)`` non."""
    return message.startswith("branche ") and not message.startswith("branche reprise")


def _messages_du_ticket(chemin: Path, ticket_id: str) -> list[str]:
    """Les messages du journal marqués ``[ticket_id]``, sans l'horodatage."""
    marque = f"[{ticket_id}] "
    messages: list[str] = []
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        morceaux = ligne.split(" — ", 1)
        if len(morceaux) == 2 and morceaux[1].startswith(marque):
            messages.append(morceaux[1][len(marque):])
    return messages


def _dernier_changes_requested(messages: list[str]) -> str | None:
    for message in reversed(messages):
        if message.startswith("CHANGES_REQUESTED tour"):
            return message
    return None


def _refus_de_fin_de_run(messages: list[str]) -> Refus | None:
    """Le refus qui clôt ``messages`` — la fin d'un seul run —, ou ``None``."""
    for index in range(len(messages) - 1, -1, -1):
        message = messages[index]
        if _est_debut_de_run(message):
            return None
        if message.startswith("securite: BLOCK"):
            return Refus("securite", message)
        if message.startswith("BLOCKED après") and "sans approbation" in message:
            motif = _dernier_changes_requested(messages[:index]) or message
            return Refus("revue", motif)
        if message.startswith(_FINS_SANS_REFUS):
            return None
    return None


def refus_precedent(chemin: object, ticket_id: str) -> Refus | None:
    """Le refus d'une porte qui a fini le run d'avant, ou ``None``.

    Le run courant a déjà écrit sa ligne ``branche …`` : tout ce qui la précède
    est l'histoire du ticket. Sans cette ligne, ou sans journal lisible, on ne
    sait pas où commence le run courant : ``None``, et la reprise garde son
    comportement d'après une coupure.
    """
    if not isinstance(chemin, Path):
        return None
    try:
        messages = _messages_du_ticket(chemin, ticket_id)
    except OSError:
        return None
    debuts = [i for i, message in enumerate(messages) if _est_debut_de_run(message)]
    if not debuts:
        return None
    return _refus_de_fin_de_run(messages[: debuts[-1]])


def retour_apres_refus(refus: Refus) -> str:
    """Ce que le codeur lit en premier quand il reprend après un refus."""
    return (
        f"Le run précédent de ce ticket s'est terminé sur un refus ({refus.porte}). "
        "Le même code renvoyé aux mêmes portes serait refusé de nouveau : "
        "corrige ce qui suit avant toute autre chose.\n\n"
        f"{refus.motif}"
    )
