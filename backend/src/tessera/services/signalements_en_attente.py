"""Signalements held back while a run owns the ide-core tree — ticket-421.

Un fichier apparu dans l'arbre pendant un run part dans le commit de suivi de
ce run, puis dans sa PR. Le signalement attend donc dans un JSON à côté de la
base, hors du dépôt, et s'écrit à la fermeture du run.
"""
import json
from pathlib import Path
from typing import TypedDict

from tessera.config import settings
from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services.run_registry import RUN_REGISTRY
from tessera.services.ticket_service import TicketService
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

NOM_FICHIER = "signalements_en_attente.json"


class SignalementEnAttente(TypedDict):
    """A report waiting for the project to be free."""

    titre: str
    type: str
    corps: str


def chemin_attente() -> Path:
    """Where the queue lives: next to the database, never inside a repository."""
    return settings.ide_db_path.parent / NOM_FICHIER


def _lire() -> list[SignalementEnAttente]:
    chemin = chemin_attente()
    if not chemin.is_file():
        return []
    try:
        brut = json.loads(chemin.read_text(encoding="utf-8"))
        return [
            SignalementEnAttente(titre=e["titre"], type=e["type"], corps=e["corps"])
            for e in brut
        ]
    except (ValueError, KeyError, TypeError):
        # Un fichier illisible est mis de côté, pas écrasé en silence.
        _logger.warning("signalements_en_attente_illisibles", extra={"chemin": str(chemin)})
        chemin.replace(chemin.with_suffix(".corrompu"))
        return []


def _ecrire(entrees: list[SignalementEnAttente]) -> None:
    chemin = chemin_attente()
    chemin.parent.mkdir(parents=True, exist_ok=True)
    temporaire = chemin.with_suffix(".tmp")
    temporaire.write_text(json.dumps(entrees, ensure_ascii=False, indent=2), encoding="utf-8")
    temporaire.replace(chemin)


def mettre_en_attente(titre: str, type_ticket: str, corps: str) -> int:
    """Append a report to the queue and return its 1-based position."""
    entrees = _lire()
    entrees.append(SignalementEnAttente(titre=titre, type=type_ticket, corps=corps))
    _ecrire(entrees)
    return len(entrees)


def construire_ticket(titre: str, type_ticket: str, corps: str) -> Ticket:
    """Build the ``todo`` ticket a report becomes."""
    return Ticket(
        id="",
        title=titre,
        type=TicketType(type_ticket),
        status=TicketStatus.todo,
        priority=TicketPriority.medium,
        agent="codeur",
        body=corps,
    )


def vider_si_libre(projet_cible: str) -> list[Ticket]:
    """Write the queued reports in arrival order, unless the project is busy again.

    Chaque signalement est retiré de l'attente une fois son fichier écrit : un
    échec en cours de route ne perd ni ne duplique rien.
    """
    ecrits: list[Ticket] = []
    service = TicketService(settings.ide_workspace_dir / projet_cible, projet_cible)
    entrees = _lire()
    while entrees and not RUN_REGISTRY.projet_occupe(projet_cible):
        premier = entrees[0]
        ecrits.append(
            service.create_ticket_sync(
                construire_ticket(premier["titre"], premier["type"], premier["corps"])
            )
        )
        entrees = entrees[1:]
        _ecrire(entrees)
    return ecrits


def installer_vidage(projet_cible: str) -> None:
    """Flush the queue each time a run on ``projet_cible`` closes."""

    def _a_la_fermeture(project_id: str) -> None:
        if project_id == projet_cible:
            vider_si_libre(projet_cible)

    RUN_REGISTRY.sur_fermeture(_a_la_fermeture)
