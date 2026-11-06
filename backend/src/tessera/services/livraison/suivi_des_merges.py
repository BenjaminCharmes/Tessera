"""State of the merges `CIWatcher` follows, bound to their PR — ticket-874.

A ticket can be delivered again with a new PR while the previous watch is still
running. Everything a watch records — its event, its result — is therefore keyed
by `(project_id, ticket_id, pr_number)`: a result is never read back as the
outcome of another PR. The task registered for a ticket is the only one allowed
to clear that ticket's state.
"""
import asyncio
from collections.abc import Awaitable, Callable

from tessera.services.livraison.controle_tete import decrire_exception
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Une PR et un ticket : ce que chaque événement et chaque résultat désigne.
CleMerge = tuple[str, str, int]


async def pr_mergee(
    etat_pr: Callable[[int], Awaitable[str]] | None, pr_number: int
) -> bool:
    """Re-read the PR; False when it cannot be read or is not merged."""
    if etat_pr is None:
        return False
    try:
        return await etat_pr(pr_number) == "merged"
    except Exception as exc:  # noqa: BLE001 — relecture best effort
        _logger.warning(
            "ci_watcher_relecture_pr_echouee",
            extra={"pr": pr_number, "erreur": decrire_exception(exc)},
        )
        return False


class SuiviDesMerges:
    """Who is watched, on which PR, and how each watch ended."""

    def __init__(self) -> None:
        # Tickets dont la PR est ouverte et attend la CI ou le merge.
        self._en_attente: dict[str, set[str]] = {}
        # Dernière PR surveillée d'un ticket, gardée après la fin de la
        # surveillance : un appel sans numéro de PR lit son résultat.
        self._pr_du_ticket: dict[tuple[str, str], int] = {}
        # Tâche inscrite pour un ticket : seule elle libère son état.
        self._tache_du_ticket: dict[tuple[str, str], asyncio.Task[None]] = {}
        # Événements signalés quand une PR quitte la file d'attente.
        self._events: dict[CleMerge, asyncio.Event] = {}
        # Résultats de merge : True = mergé, False = bloqué ou échoué.
        self._resultats: dict[CleMerge, bool] = {}

    def en_attente(self, project_id: str) -> tuple[str, ...]:
        """Ticket ids whose PR is open and waiting for CI or merge."""
        return tuple(self._en_attente.get(project_id, set()))

    def prs_en_attente(self, project_id: str) -> tuple[tuple[str, int], ...]:
        """`(ticket id, PR number)` of every PR waiting for CI or merge."""
        return tuple(
            (ticket_id, self._pr_du_ticket[(project_id, ticket_id)])
            for ticket_id in self._en_attente.get(project_id, set())
        )

    def pr_visee(
        self, project_id: str, ticket_id: str, pr_number: int | None
    ) -> int | None:
        """The PR asked for, else the last one watched for the ticket."""
        if pr_number is not None:
            return pr_number
        return self._pr_du_ticket.get((project_id, ticket_id))

    def en_cours(self, project_id: str, ticket_id: str, pr_number: int) -> bool:
        """True while this very PR is the one being watched."""
        return (
            ticket_id in self._en_attente.get(project_id, set())
            and self._pr_du_ticket.get((project_id, ticket_id)) == pr_number
        )

    def resultat(self, project_id: str, ticket_id: str, pr_number: int) -> bool | None:
        """Recorded outcome of this PR, None when there is none."""
        return self._resultats.get((project_id, ticket_id, pr_number))

    def noter(self, project_id: str, ticket_id: str, pr_number: int, merge: bool) -> None:
        """Record the outcome of this PR."""
        self._resultats[(project_id, ticket_id, pr_number)] = merge

    def inscrire(
        self, project_id: str, ticket_id: str, pr_number: int, tache: asyncio.Task[None]
    ) -> None:
        """Register the watch of `pr_number`, from the moment it is requested."""
        self._resultats.pop((project_id, ticket_id, pr_number), None)
        self._en_attente.setdefault(project_id, set()).add(ticket_id)
        self._pr_du_ticket[(project_id, ticket_id)] = pr_number
        self._tache_du_ticket[(project_id, ticket_id)] = tache

    def est_proprietaire(
        self, project_id: str, ticket_id: str, tache: asyncio.Task[None] | None
    ) -> bool:
        """True when `tache` is the task registered for the ticket."""
        return tache is not None and self._tache_du_ticket.get((project_id, ticket_id)) is tache

    def clore(self, project_id: str, ticket_id: str, pr_number: int) -> None:
        """Unregister the ticket and wake whoever waits for this PR."""
        self._en_attente.get(project_id, set()).discard(ticket_id)
        self._tache_du_ticket.pop((project_id, ticket_id), None)
        evt = self._events.pop((project_id, ticket_id, pr_number), None)
        if evt is not None:
            evt.set()

    async def remplacer(self, project_id: str, ticket_id: str) -> None:
        """Cancel the watch registered for the ticket and wait until it is over.

        The state is cleared here too: a task cancelled before its first step
        never reaches its own cleanup.
        """
        cle = (project_id, ticket_id)
        ancienne = self._tache_du_ticket.get(cle)
        if ancienne is None:
            return
        ancienne.cancel()
        await asyncio.gather(ancienne, return_exceptions=True)
        self.clore(project_id, ticket_id, self._pr_du_ticket[cle])

    async def attendre(
        self, project_id: str, ticket_id: str, pr_number: int, timeout_s: float
    ) -> bool:
        """Wait for the end of the watch of this PR; False on timeout."""
        cle = (project_id, ticket_id, pr_number)
        evt = self._events.setdefault(cle, asyncio.Event())
        try:
            await asyncio.wait_for(evt.wait(), timeout=timeout_s)
        except TimeoutError:
            _logger.warning(
                "attente_merge_expiree",
                extra={"project": project_id, "ticket": ticket_id, "pr": pr_number},
            )
            return False
        # Sans résultat enregistré, la tâche a été annulée : pas mergé.
        return self._resultats.get(cle, False)
