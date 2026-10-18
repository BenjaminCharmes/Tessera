"""The queue of a running `queue` run, which accepts tickets while it runs — ticket-478.

`run_queue` iterated over a frozen copy of the ids, so a ticket written while
the queue ran needed a second run, and the second `POST /run` took a 409
(ADR-038). The queue is now a list the loop and the router share: the loop
reads it again at every step, the router appends to it.

Tout se passe dans la boucle asyncio unique : aucun verrou, à condition qu'il
n'y ait pas d'`await` entre le contrôle d'ouverture et l'ajout.
"""
from tessera.models.ticket import TicketStatus
from tessera.services.ticket_service import TicketService

_TERMINES = (TicketStatus.done, TicketStatus.cancelled)


class FileFermee(Exception):
    """The queue has finished reading its list: nothing added now would run."""


class FileVivante(list[str]):
    """Ticket ids of a queue, in run order, still open to additions.

    Une sous-classe de `list` et non un objet à part : l'itérateur d'une
    liste relit sa longueur à chaque pas, donc un id ajouté pendant la boucle
    est vu sans rien changer à `run_queue`, et tout appelant qui passe une
    simple liste continue de fonctionner.
    """

    def __init__(self, ticket_ids: list[str] | None = None) -> None:
        super().__init__(ticket_ids or [])
        self.ouverte = True

    def fermer(self) -> None:
        """Stop accepting additions; called once the loop has read its last id."""
        self.ouverte = False

    def ajouter(self, ticket_ids: list[str]) -> list[str]:
        """Append the ids not already queued; return the ones actually added."""
        if not self.ouverte:
            raise FileFermee("La file a fini de lire sa liste.")
        ajoutes: list[str] = []
        for ticket_id in ticket_ids:
            if ticket_id not in self:
                self.append(ticket_id)
                ajoutes.append(ticket_id)
        return ajoutes


def fermer_si_vivante(ticket_ids: list[str]) -> None:
    """Close `ticket_ids` when it is a live queue; a plain list is left alone."""
    if isinstance(ticket_ids, FileVivante):
        ticket_ids.fermer()


async def trier_ajouts(
    file: FileVivante, ticket_svc: TicketService, ticket_ids: list[str]
) -> tuple[list[str], dict[str, str], dict[str, str]]:
    """Split the requested ids into (to add, ignored, refused).

    Ignoré : déjà dans la file, ou déjà terminé. Refusé : introuvable, ou
    une dépendance qui n'est ni dans la file ni terminée. Un ticket accepté
    plus haut dans la même demande compte comme dans la file pour les
    suivants.
    """
    acceptes: list[str] = []
    ignores: dict[str, str] = {}
    refuses: dict[str, str] = {}
    for ticket_id in ticket_ids:
        if ticket_id in file or ticket_id in acceptes:
            ignores[ticket_id] = "déjà dans la file"
            continue
        ticket = await ticket_svc.get_ticket(ticket_id)
        if ticket is None:
            refuses[ticket_id] = "ticket introuvable"
        elif ticket.status in _TERMINES:
            ignores[ticket_id] = "déjà terminé"
        else:
            manquante = await _dependance_manquante(
                file, ticket_svc, ticket.depends_on, acceptes
            )
            if manquante is None:
                acceptes.append(ticket_id)
            else:
                refuses[ticket_id] = f"dépendance {manquante} ni dans la file ni terminée"
    return acceptes, ignores, refuses


async def _dependance_manquante(
    file: FileVivante,
    ticket_svc: TicketService,
    depends_on: list[str],
    acceptes: list[str],
) -> str | None:
    """The first dependency neither queued nor done, or None when all are met."""
    for dep in depends_on:
        if dep in file or dep in acceptes:
            continue
        ticket_dep = await ticket_svc.get_ticket(dep)
        if ticket_dep is None or ticket_dep.status != TicketStatus.done:
            return dep
    return None
