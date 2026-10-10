"""Watch CI and merge in the background, one delivery per project — ticket-306.

After livrer_phase_1 opens the PR and releases the run lock (ADR-051), this
service runs livrer_phase_2 (CI wait + merge) in a background asyncio task.

Serialisation rule: at most one delivery per project is active at any time.
A second call for the same project waits for the first to finish before
starting. Two different projects are fully independent.

When CI is red, CIWatcher emits ticket_status_changed (blocked) so the board
reflects the outcome, then ci_merge_done with merged=False and an arret naming
the PR number.  The ticket file in the working tree is never touched — the
board reads the event; the pipeline log keeps the trace (ticket-392).

Error handling (ticket-328): any exception raised by livraison_phase_2, or a
timeout of the entire phase 2 (including CI wait), emits ci_merge_done with
merged=False and an arret describing the cause, then transitions the ticket to
blocked.  A CancelledError from backend shutdown is NOT treated as an error —
no ci_merge_done is emitted.

Shutdown: call arreter() to cancel all running tasks without raising exceptions.
"""
import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path

from tessera.models.ticket import TicketStatus
from tessera.services.livraison import Livraison
from tessera.services.pipeline_events import EventCallback, EventType, OrchestratorEvent
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Borne globale de la phase 2 (attente CI + merge). Supérieure à
#: _ATTENTE_CI_MAX_S (900 s) pour couvrir également les appels réseau du merge.
_TIMEOUT_PHASE2_S = 1200.0


class CIWatcher:
    """Background CI watcher — at most one active delivery per project."""

    def __init__(self, timeout_phase2_s: float = _TIMEOUT_PHASE2_S) -> None:
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
        # Résultats de merge : True = mergé, False = bloqué/échoué.
        # Clé : "project_id:ticket_id".
        self._resultats_merge: dict[str, bool] = {}
        # Borne temporelle de la phase 2 entière. Paramétrable pour les tests.
        self._timeout_phase2_s = timeout_phase2_s

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
        pipeline_log_path: Path | None = None,
    ) -> None:
        """Start watching `pr_number` for `ticket_id` in the background.

        Returns immediately; the background task emits ci_merge_done when done.
        A second call for the same project waits for the first to finish.

        When the merge fails, writes a line to `pipeline_log_path` (if given).
        The ticket file in the working tree is never modified (ticket-392).
        """
        # Le ticket est en attente dès l'inscription, même avant que le
        # sémaphore soit acquis : `en_attente` doit le lister pendant l'attente
        # de CI **et** pendant l'attente du sémaphore.
        self._en_attente.setdefault(project_id, set()).add(ticket_id)

        task = asyncio.create_task(
            self._surveiller_impl(
                project_id, ticket_id, pr_number, livraison_phase_2, on_event,
                pipeline_log_path,
            ),
            name=f"ci-watcher:{project_id}:{ticket_id}",
        )
        self._taches.add(task)
        task.add_done_callback(self._taches.discard)

    def en_attente(self, project_id: str) -> tuple[str, ...]:
        """Ticket ids whose PR is open and waiting for CI or merge."""
        return tuple(self._en_attente.get(project_id, set()))

    async def attendre_merge(self, project_id: str, ticket_id: str) -> bool:
        """Wait until the ticket is no longer waiting for CI or merge.

        Returns True if the ticket was merged, False if it was blocked or failed.
        Returns True immediately when the ticket was never registered (safe
        default — not applicable to this queue).

        Safe to call from a queue loop: a dependent ticket suspends here until
        the background task signals completion.
        """
        cle = f"{project_id}:{ticket_id}"
        if ticket_id not in self._en_attente.get(project_id, set()):
            # Already finished or never registered — return recorded result.
            return self._resultats_merge.get(cle, True)
        if cle not in self._events_merge:
            self._events_merge[cle] = asyncio.Event()
        await self._events_merge[cle].wait()
        return self._resultats_merge.get(cle, True)

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
        pipeline_log_path: Path | None,
    ) -> None:
        sem = self._semaphore_du_projet(project_id)
        try:
            async with sem:
                arret_erreur: str | None = None
                try:
                    await asyncio.wait_for(
                        self._livrer_et_emettre(
                            project_id, ticket_id, pr_number, livraison_phase_2,
                            on_event, pipeline_log_path,
                        ),
                        timeout=self._timeout_phase2_s,
                    )
                except asyncio.TimeoutError:
                    arret_erreur = f"délai dépassé ({self._timeout_phase2_s:.0f}s)"
                    _logger.warning(
                        "ci_watcher_timeout",
                        extra={"project": project_id, "ticket": ticket_id},
                    )
                except Exception as exc:  # noqa: BLE001
                    arret_erreur = f"erreur inattendue : {exc}"
                    _logger.exception(
                        "ci_watcher_error",
                        extra={"project": project_id, "ticket": ticket_id},
                    )
                if arret_erreur is not None:
                    await self._emettre_echec(
                        project_id, ticket_id, pr_number, arret_erreur, on_event,
                        pipeline_log_path,
                    )
        except asyncio.CancelledError:
            _logger.info(
                "ci_watcher_cancelled",
                extra={"project": project_id, "ticket": ticket_id},
            )
        except Exception:  # noqa: BLE001
            # L'émission elle-même a échoué — on journalise sans relancer.
            _logger.exception(
                "ci_watcher_emit_error",
                extra={"project": project_id, "ticket": ticket_id},
            )
        finally:
            self._en_attente.get(project_id, set()).discard(ticket_id)
            # Signaler les éventuels appelants d'`attendre_merge`.
            cle = f"{project_id}:{ticket_id}"
            evt = self._events_merge.pop(cle, None)
            if evt is not None:
                evt.set()

    async def _emettre_echec(
        self,
        project_id: str,
        ticket_id: str,
        pr_number: int,
        arret: str,
        on_event: EventCallback,
        pipeline_log_path: Path | None,
    ) -> None:
        """Emit ticket_status_changed(blocked) then ci_merge_done(merged=False)."""
        self._resultats_merge[f"{project_id}:{ticket_id}"] = False
        self._ecrire_log_blocage(pipeline_log_path, ticket_id, pr_number, arret)
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
            "ci_watcher_blocked",
            extra={"project": project_id, "ticket": ticket_id, "pr": pr_number, "arret": arret},
        )

    async def _livrer_et_emettre(
        self,
        project_id: str,
        ticket_id: str,
        pr_number: int,
        livraison_phase_2: Callable[[int], Awaitable[Livraison]],
        on_event: EventCallback,
        pipeline_log_path: Path | None,
    ) -> None:
        livraison = await livraison_phase_2(pr_number)

        if not livraison.merged:
            # CI rouge ou merge refusé : signaler sans toucher la fiche (ticket-392).
            arret = livraison.arret or f"CI rouge : la PR #{pr_number} reste ouverte."
            self._resultats_merge[f"{project_id}:{ticket_id}"] = False
            self._ecrire_log_blocage(pipeline_log_path, ticket_id, pr_number, arret)
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
            self._resultats_merge[f"{project_id}:{ticket_id}"] = True
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

    def _ecrire_log_blocage(
        self,
        pipeline_log_path: Path | None,
        ticket_id: str,
        pr_number: int,
        arret: str,
    ) -> None:
        """Write a blocking delivery entry to the pipeline log."""
        if pipeline_log_path is None:
            return
        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        line = (
            f"- {ts} — [{ticket_id}] livraison: arrêt — "
            f"PR #{pr_number} non mergée : {arret[:200]}\n"
        )
        try:
            pipeline_log_path.parent.mkdir(parents=True, exist_ok=True)
            with pipeline_log_path.open("a", encoding="utf-8") as f:
                f.write(line)
        except Exception as exc:  # noqa: BLE001
            _logger.warning("pipeline_log_write_failed", extra={"error": str(exc)})

#: Instance partagée par tous les routeurs. Un singleton en mémoire suffit
#: pour un backend local (ADR-038).
CI_WATCHER = CIWatcher()
