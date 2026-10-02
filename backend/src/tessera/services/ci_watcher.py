"""Watch CI and merge in the background, one delivery per project — ticket-306.

After livrer_phase_1 opens the PR and releases the run lock (ADR-051), this
service runs livrer_phase_2 (CI wait + merge) in a background asyncio task.

Serialisation rule: at most one delivery per project is active at any time.
A second call for the same project waits for the first to finish before
starting. Two different projects are fully independent.

When CI is red, CIWatcher emits ticket_status_changed (blocked) so the board
reflects the outcome, then ci_merge_done with merged=False and an arret naming
the PR number.

Shutdown: call arreter() to cancel all running tasks without raising exceptions.
"""
import asyncio
from collections.abc import Awaitable, Callable

from tessera.models.ticket import TicketStatus
from tessera.services.livraison import Livraison
from tessera.services.pipeline_events import EventCallback, EventType, OrchestratorEvent
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)


class CIWatcher:
    """Background CI watcher — at most one active delivery per project."""

    def __init__(self) -> None:
        # Un sémaphore par projet : valeur 1 = une seule livraison active à
        # la fois. Un second appel attend derrière le premier sans le rejeter.
        self._semaphores: dict[str, asyncio.Semaphore] = {}
        # Tickets dont la PR est ouverte et attend la CI ou le merge.
        self._en_attente: dict[str, set[str]] = {}
        # Tâches asyncio en cours — tenues pour pouvoir les annuler à l'arrêt.
        self._taches: set[asyncio.Task[None]] = set()
        # Événements signalés quand un ticket quitte la file d'attente.
        # Clé : "project_id:ticket_id".
        self._events_merge: dict[str, asyncio.Event] = {}

    # ------------------------------------------------------------------
    # Interface publique
    # ------------------------------------------------------------------

    async def surveiller(
        self,
        project_id: str,
        ticket_id: str,
        pr_number: int,
        livraison_phase_2: Callable[[int], Awaitable[Livraison]],
        on_event: EventCallback,
    ) -> None:
        """Start watching `pr_number` for `ticket_id` in the background.

        Returns immediately; the background task emits ci_merge_done when done.
        A second call for the same project waits for the first to finish.
        """
        # Le ticket est en attente dès l'inscription, même avant que le
        # sémaphore soit acquis : `en_attente` doit le lister pendant l'attente
        # de CI **et** pendant l'attente du sémaphore.
        self._en_attente.setdefault(project_id, set()).add(ticket_id)

        task = asyncio.create_task(
            self._surveiller_impl(
                project_id, ticket_id, pr_number, livraison_phase_2, on_event
            ),
            name=f"ci-watcher:{project_id}:{ticket_id}",
        )
        self._taches.add(task)
        task.add_done_callback(self._taches.discard)

    def en_attente(self, project_id: str) -> tuple[str, ...]:
        """Ticket ids whose PR is open and waiting for CI or merge."""
        return tuple(self._en_attente.get(project_id, set()))

    async def attendre_merge(self, project_id: str, ticket_id: str) -> None:
        """Wait until the ticket is no longer waiting for CI or merge.

        Returns immediately if the ticket is already done or was never
        registered. Safe to call from a queue loop: a dependent ticket
        suspends here until the background task signals completion.
        """
        if ticket_id not in self._en_attente.get(project_id, set()):
            return
        cle = f"{project_id}:{ticket_id}"
        if cle not in self._events_merge:
            self._events_merge[cle] = asyncio.Event()
        await self._events_merge[cle].wait()

    async def arreter(self) -> None:
        """Cancel all running tasks and wait for them to finish.

        Never raises — cancellation is a clean shutdown, not an error.
        """
        taches = list(self._taches)
        for tache in taches:
            tache.cancel()
        if taches:
            await asyncio.gather(*taches, return_exceptions=True)

    # ------------------------------------------------------------------
    # Implémentation interne
    # ------------------------------------------------------------------

    def _semaphore_du_projet(self, project_id: str) -> asyncio.Semaphore:
        if project_id not in self._semaphores:
            self._semaphores[project_id] = asyncio.Semaphore(1)
        return self._semaphores[project_id]

    async def _surveiller_impl(
        self,
        project_id: str,
        ticket_id: str,
        pr_number: int,
        livraison_phase_2: Callable[[int], Awaitable[Livraison]],
        on_event: EventCallback,
    ) -> None:
        sem = self._semaphore_du_projet(project_id)
        try:
            async with sem:
                await self._livrer_et_emettre(
                    project_id, ticket_id, pr_number, livraison_phase_2, on_event
                )
        except asyncio.CancelledError:
            _logger.info(
                "ci_watcher_cancelled",
                extra={"project": project_id, "ticket": ticket_id},
            )
        except Exception:  # noqa: BLE001
            _logger.exception(
                "ci_watcher_error",
                extra={"project": project_id, "ticket": ticket_id},
            )
        finally:
            self._en_attente.get(project_id, set()).discard(ticket_id)
            # Signaler les éventuels appelants d'`attendre_merge`.
            cle = f"{project_id}:{ticket_id}"
            evt = self._events_merge.pop(cle, None)
            if evt is not None:
                evt.set()

    async def _livrer_et_emettre(
        self,
        project_id: str,
        ticket_id: str,
        pr_number: int,
        livraison_phase_2: Callable[[int], Awaitable[Livraison]],
        on_event: EventCallback,
    ) -> None:
        livraison = await livraison_phase_2(pr_number)

        if not livraison.merged:
            # CI rouge ou merge refusé : le ticket passe en blocked.
            arret = livraison.arret or f"CI rouge : la PR #{pr_number} reste ouverte."
            await on_event(
                OrchestratorEvent(
                    type=EventType.TICKET_STATUS_CHANGED,
                    ticket_id=ticket_id,
                    project_id=project_id,
                    data={"status": TicketStatus.blocked.value},
                )
            )
            await on_event(
                OrchestratorEvent(
                    type=EventType.CI_MERGE_DONE,
                    ticket_id=ticket_id,
                    project_id=project_id,
                    data={
                        "project_id": project_id,
                        "ticket_id": ticket_id,
                        "pr_number": pr_number,
                        "merged": False,
                        "arret": arret,
                    },
                )
            )
            _logger.warning(
                "ci_merge_blocked",
                extra={"project": project_id, "ticket": ticket_id, "pr": pr_number},
            )
        else:
            await on_event(
                OrchestratorEvent(
                    type=EventType.CI_MERGE_DONE,
                    ticket_id=ticket_id,
                    project_id=project_id,
                    data={
                        "project_id": project_id,
                        "ticket_id": ticket_id,
                        "pr_number": pr_number,
                        "merged": True,
                        "arret": None,
                    },
                )
            )
            _logger.info(
                "ci_merge_done",
                extra={"project": project_id, "ticket": ticket_id, "pr": pr_number},
            )


#: Instance partagée par tous les routeurs. Un singleton en mémoire suffit
#: pour un backend local (ADR-038).
CI_WATCHER = CIWatcher()
