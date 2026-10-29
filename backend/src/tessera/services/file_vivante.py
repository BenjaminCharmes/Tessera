"""The queue of a running `queue` run, which accepts tickets while it runs — ticket-478.

`run_queue` iterated over a frozen copy of the ids, so a ticket written while
the queue ran needed a second run, and the second `POST /run` took a 409
(ADR-038). The queue is now a list the loop and the router share: the loop
reads it again at every step, the router appends to it.

Tout se passe dans la boucle asyncio unique : aucun verrou, à condition qu'il
n'y ait pas d'`await` entre le contrôle d'ouverture et l'ajout.
"""
from collections.abc import Awaitable, Callable
from typing import Protocol

from tessera.models.ticket import Ticket, TicketStatus
from tessera.services.ticket_service import TicketService, ticket_depuis_contenu

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
        # Rang (0-based) du ticket que la boucle traite ; -1 avant le premier.
        self._position = -1

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

    def ajouter_acceptes(
        self, acceptes: list[str], ignores: dict[str, str]
    ) -> list[str]:
        """Append the ids `trier_ajouts` accepted; file the others under `ignores`.

        Un id accepté que `ajouter` n'ajoute pas est entré dans la file pendant
        le tri (un appel concurrent) : ignoré, jamais perdu (ticket-658).
        """
        ajoutes = self.ajouter(acceptes)
        for ticket_id in acceptes:
            if ticket_id not in ajoutes:
                ignores[ticket_id] = "déjà dans la file"
        return ajoutes

    def marquer_position(self, index: int) -> None:
        """Record the 1-based position the loop is handling (ticket-513)."""
        self._position = index - 1

    def restants(self) -> list[str]:
        """Ids still waiting behind the ticket being handled, additions included.

        Même sens que `restants` dans `queue_progress` : le ticket traité
        n'en fait pas partie (il est `ticket_courant`). Avant le premier
        ticket, `_position` vaut -1 et c'est la file entière (ticket-560).
        """
        return list(self[self._position + 1 :])

    def retirer(
        self, ticket_ids: list[str]
    ) -> tuple[list[str], dict[str, str], dict[str, str]]:
        """Remove the ids not started yet; return (removed, ignored, refused).

        Refusé : le ticket en cours, ou un ticket que la boucle a déjà passé.
        Ignoré : absent de la file. Comme `ajouter`, aucun `await` : la boucle
        ne peut pas avancer entre le contrôle et le retrait.
        """
        if not self.ouverte:
            raise FileFermee("La file a fini de lire sa liste.")
        retires: list[str] = []
        ignores: dict[str, str] = {}
        refuses: dict[str, str] = {}
        for ticket_id in ticket_ids:
            if ticket_id not in self:
                ignores[ticket_id] = "absent de la file"
                continue
            rang = self.index(ticket_id)
            if rang == self._position:
                refuses[ticket_id] = "en cours : utiliser stop"
            elif rang < self._position:
                refuses[ticket_id] = "déjà traité par la file"
            else:
                del self[rang]
                retires.append(ticket_id)
        return retires, ignores, refuses


def marquer_position_si_vivante(ticket_ids: list[str], index: int) -> None:
    """Tell a live queue which 1-based position the loop is on; a plain list is left alone."""
    if isinstance(ticket_ids, FileVivante):
        ticket_ids.marquer_position(index)


def fermer_si_vivante(ticket_ids: list[str]) -> None:
    """Close `ticket_ids` when it is a live queue; a plain list is left alone."""
    if isinstance(ticket_ids, FileVivante):
        ticket_ids.fermer()


LecteurDeRepli = Callable[[str], Awaitable[Ticket | None]]


class _LecteurSurLaBase(Protocol):
    async def lire_ticket_sur_la_base(
        self, ticket_id: str, *, fetch: bool = True
    ) -> tuple[str, str] | None: ...


def lecteur_sur_la_base(workspace: _LecteurSurLaBase, project_id: str) -> LecteurDeRepli:
    """A fallback reader of tickets on ``origin/<base>`` (ticket-504).

    Un ticket écrit après le lancement de la file n'est jamais dans l'arbre du
    run, qui est sur la branche du ticket en cours : il n'est que sur la base.
    Contenu illisible : None, donc le ticket reste refusé. Le lecteur ne fait
    qu'un `fetch`, à sa première lecture : la base est lue une fois par
    requête, puis chaque ticket y est cherché sans nouveau `fetch` (ticket-658).
    """
    etat = {"fetch_fait": False}

    async def lire(ticket_id: str) -> Ticket | None:
        # Posé avant l'await : même une lecture qui échoue ne refait pas le fetch.
        fetch = not etat["fetch_fait"]
        etat["fetch_fait"] = True
        lu = await workspace.lire_ticket_sur_la_base(ticket_id, fetch=fetch)
        if lu is None:
            return None
        try:
            return ticket_depuis_contenu(lu[0], lu[1], project_id)
        except ValueError:
            return None

    return lire


async def _lire(
    ticket_svc: TicketService, repli: LecteurDeRepli | None, ticket_id: str
) -> Ticket | None:
    """The ticket from the work tree, else from the fallback reader if any."""
    ticket = await ticket_svc.get_ticket(ticket_id)
    if ticket is None and repli is not None:
        return await repli(ticket_id)
    return ticket


async def trier_ajouts(
    file: FileVivante,
    ticket_svc: TicketService,
    ticket_ids: list[str],
    repli: LecteurDeRepli | None = None,
) -> tuple[list[str], dict[str, str], dict[str, str]]:
    """Split the requested ids into (to add, ignored, refused).

    Ignoré : déjà dans la file, ou déjà terminé. Refusé : introuvable, ou
    une dépendance qui n'est ni dans la file ni terminée. Un ticket accepté
    plus haut dans la même demande compte comme dans la file pour les
    suivants. `repli` lit un ticket absent de l'arbre (ticket-504).
    """
    acceptes: list[str] = []
    ignores: dict[str, str] = {}
    refuses: dict[str, str] = {}
    for ticket_id in ticket_ids:
        if ticket_id in file or ticket_id in acceptes:
            ignores[ticket_id] = "déjà dans la file"
            continue
        ticket = await _lire(ticket_svc, repli, ticket_id)
        if ticket is None:
            refuses[ticket_id] = "ticket introuvable"
        elif ticket.status in _TERMINES:
            ignores[ticket_id] = "déjà terminé"
        else:
            manquante = await _dependance_manquante(
                file, ticket_svc, ticket.depends_on, acceptes, repli
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
    repli: LecteurDeRepli | None = None,
) -> str | None:
    """The first dependency neither queued nor done, or None when all are met."""
    for dep in depends_on:
        if dep in file or dep in acceptes:
            continue
        ticket_dep = await _lire(ticket_svc, repli, dep)
        if ticket_dep is None or ticket_dep.status != TicketStatus.done:
            return dep
    return None
