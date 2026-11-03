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

Network errors (ticket-405): an httpx.TransportError (ReadTimeout…) during
phase 2 does not prove the delivery failed — GitHub may have merged the PR
before the answer was lost.  When the caller provides `etat_pr`, the watcher
re-reads the PR first; a merged PR is a success, logged as such.  Every failure
message names the exception type, even when its text is empty.

Retry (ticket-739): when the re-read PR is not merged, phase 2 is replayed once,
under the bound each pass has, and the pipeline log says so. A second network
error, or any other exception, is a failure as before.

Shutdown: call arreter() to cancel all running tasks without raising exceptions.
"""
import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path

import httpx

from tessera.models.ticket import TicketStatus
from tessera.services.controle_tete import (
    ControleTete as ControleTete,
    EstAncetre as EstAncetre,
    TetePr as TetePr,
    decrire_exception as decrire_exception,
    verifier_tete,
)
from tessera.services.journal_ci_watcher import (
    ecrire_ligne_log,
    ecrire_log_blocage,
    ecrire_log_merge,
)
from tessera.services.livraison import Livraison
from tessera.services.mise_a_jour_pr import DELAI_MISE_A_JOUR_S, MiseAJourPr, mettre_a_jour_la_pr
from tessera.services.pipeline_events import EventCallback, EventType, OrchestratorEvent
from tessera.services.realignement_base import Realignement, realigner_base
from tessera.services.run_registry import RUN_REGISTRY
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Borne globale de la phase 2 (attente CI + merge). Supérieure à
#: _ATTENTE_CI_MAX_S (900 s) pour couvrir également les appels réseau du merge.
_TIMEOUT_PHASE2_S = 1200.0

#: Relit l'état d'une PR : « open », « closed », « merged » ou « unknown ».
EtatPr = Callable[[int], Awaitable[str]]

#: Une passe de la phase 2 : le contrôle de tête et la livraison, ou l'arrêt.
_Passe = tuple[str | None, Livraison | None]


class CIWatcher:
    """Background CI watcher — at most one active delivery per project."""

    def __init__(
        self,
        timeout_phase2_s: float = _TIMEOUT_PHASE2_S,
        timeout_mise_a_jour_s: float = DELAI_MISE_A_JOUR_S,
    ) -> None:
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
        # Réalignement de la base demandé par surveiller (ticket-422).
        # Clé : "project_id:ticket_id".
        self._realignements: dict[str, Realignement] = {}
        # Borne temporelle de la phase 2 entière. Paramétrable pour les tests.
        self._timeout_phase2_s = timeout_phase2_s
        # Borne de la mise à jour d'une PR conflictuelle (ticket-733).
        self._timeout_mise_a_jour_s = timeout_mise_a_jour_s

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
        etat_pr: EtatPr | None = None,
        realignement: Realignement | None = None,
        controle_tete: ControleTete | None = None,
        mise_a_jour: MiseAJourPr | None = None,
    ) -> None:
        """Start watching `pr_number` for `ticket_id` in the background.

        Returns immediately; the background task emits ci_merge_done when done.
        A second call for the same project waits for the first to finish.

        When the merge fails, writes a line to `pipeline_log_path` (if given).
        The ticket file in the working tree is never modified (ticket-392).
        `etat_pr` lets the watcher re-read the PR after a network error
        (ticket-405); without it, a network error is a failure.
        `realignement` asks for the local base to be fast-forwarded once the
        PR is merged, when no run holds the project (ticket-422).
        `controle_tete` makes the watcher refuse to merge a PR whose head is
        no longer the pushed commit (ticket-492).
        `mise_a_jour` updates a PR the CI found conflicting, once, then the
        watcher follows its new head; without it the ticket stops on « à
        rebaser » (ticket-733).
        """
        # Un résultat d'une surveillance précédente du même ticket serait relu
        # comme celui de cette PR-ci.
        self._resultats_merge.pop(f"{project_id}:{ticket_id}", None)
        if realignement is not None:
            self._realignements[f"{project_id}:{ticket_id}"] = realignement
        # Le ticket est en attente dès l'inscription, même avant que le
        # sémaphore soit acquis : `en_attente` doit le lister pendant l'attente
        # de CI **et** pendant l'attente du sémaphore.
        self._en_attente.setdefault(project_id, set()).add(ticket_id)

        task = asyncio.create_task(
            self._surveiller_impl(
                project_id, ticket_id, pr_number, livraison_phase_2, on_event,
                pipeline_log_path, etat_pr, controle_tete, mise_a_jour,
            ),
            name=f"ci-watcher:{project_id}:{ticket_id}",
        )
        self._taches.add(task)
        task.add_done_callback(self._taches.discard)

    def en_attente(self, project_id: str) -> tuple[str, ...]:
        """Ticket ids whose PR is open and waiting for CI or merge."""
        return tuple(self._en_attente.get(project_id, set()))

    async def attendre_merge(
        self,
        project_id: str,
        ticket_id: str,
        pr_number: int | None = None,
        etat_pr: EtatPr | None = None,
    ) -> bool:
        """Wait until the ticket is no longer waiting for CI or merge.

        Returns True if the ticket was merged, False if it was blocked or failed.

        A ticket that is not registered and has no recorded result is unknown
        to the watcher. When the caller gives its `pr_number`, the PR is re-read
        through `etat_pr` and only a ``merged`` PR counts as merged — fails
        closed (ADR-039): a missing reader, an error or an unknown state is
        False. Without a PR number there is nothing to wait for: True.

        Safe to call from a queue loop: a dependent ticket suspends here until
        the background task signals completion.
        """
        cle = f"{project_id}:{ticket_id}"
        if ticket_id not in self._en_attente.get(project_id, set()):
            if cle in self._resultats_merge:
                return self._resultats_merge[cle]
            if pr_number is None:
                return True
            return await self._pr_mergee(etat_pr, pr_number)
        if cle not in self._events_merge:
            self._events_merge[cle] = asyncio.Event()
        await self._events_merge[cle].wait()
        # Sans résultat enregistré, la tâche a été annulée : pas mergé.
        return self._resultats_merge.get(cle, False)

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
        etat_pr: EtatPr | None = None,
        controle_tete: ControleTete | None = None,
        mise_a_jour: MiseAJourPr | None = None,
    ) -> None:
        sem = self._semaphore_du_projet(project_id)
        try:
            async with sem:
                arret_erreur = await self._phase_2_avec_reprise(
                    project_id, ticket_id, pr_number, livraison_phase_2,
                    on_event, pipeline_log_path, etat_pr, controle_tete, mise_a_jour,
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
            self._realignements.pop(cle, None)
            evt = self._events_merge.pop(cle, None)
            if evt is not None:
                evt.set()

    async def _phase_2_avec_reprise(
        self,
        project_id: str,
        ticket_id: str,
        pr_number: int,
        livraison_phase_2: Callable[[int], Awaitable[Livraison]],
        on_event: EventCallback,
        pipeline_log_path: Path | None,
        etat_pr: EtatPr | None,
        controle_tete: ControleTete | None,
        mise_a_jour: MiseAJourPr | None,
    ) -> str | None:
        """Run phase 2; the failure line, or None when settled.

        Chaque passage a sa borne, dans `_passe` : une mise à jour a la sienne
        (ticket-733). Une erreur réseau sur une PR toujours ouverte rejoue la
        phase 2 une fois (ticket-739) : c'est sûr, elle relit la CI, refuse une
        tête qui n'est plus `pushed_sha`, et le merge est lié à `pushed_sha`
        (ADR-039).
        """
        reprise_faite = False
        while True:
            try:
                await self._livrer_et_emettre(
                    project_id, ticket_id, pr_number, livraison_phase_2,
                    on_event, pipeline_log_path, controle_tete, mise_a_jour,
                )
                return None
            except asyncio.TimeoutError:
                _logger.warning(
                    "ci_watcher_timeout",
                    extra={"project": project_id, "ticket": ticket_id},
                )
                return f"délai dépassé ({self._timeout_phase2_s:.0f}s)"
            except httpx.TransportError as exc:
                # Une réponse perdue ne dit pas que l'action a échoué : on
                # relit la PR avant de conclure (ticket-405).
                if await self._pr_mergee(etat_pr, pr_number):
                    await self._succes_malgre_erreur_reseau(
                        project_id, ticket_id, pr_number, exc, on_event,
                        pipeline_log_path,
                    )
                    return None
                if reprise_faite:
                    return self._arret_erreur(project_id, ticket_id, exc)
                reprise_faite = True
                self._noter_reprise(pipeline_log_path, ticket_id, pr_number, exc)
            except Exception as exc:  # noqa: BLE001
                return self._arret_erreur(project_id, ticket_id, exc)

    def _arret_erreur(
        self, project_id: str, ticket_id: str, exc: BaseException
    ) -> str:
        """Log the exception being handled and return its stop line."""
        _logger.exception(
            "ci_watcher_error",
            extra={"project": project_id, "ticket": ticket_id},
        )
        return f"erreur inattendue : {decrire_exception(exc)}"

    def _noter_reprise(
        self,
        pipeline_log_path: Path | None,
        ticket_id: str,
        pr_number: int,
        exc: BaseException,
    ) -> None:
        """Say in the pipeline log that phase 2 is replayed, and why."""
        ecrire_ligne_log(
            pipeline_log_path,
            ticket_id,
            f"livraison: nouvelle tentative de la PR #{pr_number} après une "
            f"erreur réseau ({decrire_exception(exc)}), PR non mergée",
        )

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
        ecrire_log_blocage(pipeline_log_path, ticket_id, pr_number, arret)
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
        controle_tete: ControleTete | None = None,
        mise_a_jour: MiseAJourPr | None = None,
    ) -> None:
        arret, livraison = await self._passe(pr_number, livraison_phase_2, controle_tete)
        if (
            livraison is not None
            and livraison.a_mettre_a_jour
            and mise_a_jour is not None
            and controle_tete is not None
        ):
            # Une seule mise à jour par surveillance : un second `conflicting`
            # retombe sur l'arrêt habituel (ticket-733).
            suite = await mettre_a_jour_la_pr(
                project_id=project_id, ticket_id=ticket_id, pr_number=pr_number,
                controle=controle_tete, mise_a_jour=mise_a_jour,
                journaliser=lambda texte: self._journaliser_mise_a_jour(
                    pipeline_log_path, project_id, ticket_id, texte
                ),
                delai_s=self._timeout_mise_a_jour_s,
            )
            arret = suite.arret
            if arret is None:
                arret, livraison = await self._passe(
                    pr_number, livraison_phase_2, suite.controle
                )
        if arret is None and livraison is not None and livraison.merged:
            await self._emettre_succes(
                project_id, ticket_id, pr_number, on_event, pipeline_log_path
            )
            return
        # La tête a bougé depuis le push (ticket-492), CI rouge ou merge refusé :
        # signaler sans toucher la fiche (ticket-392). La PR reste ouverte.
        if arret is None and livraison is not None:
            arret = livraison.arret or f"CI rouge : la PR #{pr_number} reste ouverte."
        await self._emettre_echec(
            project_id, ticket_id, pr_number, arret or "livraison sans issue", on_event,
            pipeline_log_path,
        )

    async def _passe(
        self,
        pr_number: int,
        livraison_phase_2: Callable[[int], Awaitable[Livraison]],
        controle_tete: ControleTete | None,
    ) -> _Passe:
        """One pass of phase 2 — head check, then delivery — under its own bound."""

        async def corps() -> _Passe:
            arret = await verifier_tete(controle_tete, pr_number)
            if arret is not None:
                return arret, None
            return None, await livraison_phase_2(pr_number)

        return await asyncio.wait_for(corps(), timeout=self._timeout_phase2_s)

    def _journaliser_mise_a_jour(
        self,
        pipeline_log_path: Path | None,
        project_id: str,
        ticket_id: str,
        texte: str,
    ) -> None:
        """Journal line of an update; without a log path, the logger event carries it."""
        ecrire_ligne_log(pipeline_log_path, ticket_id, texte)
        _logger.info(
            "ci_watcher_pr_mise_a_jour",
            extra={"project": project_id, "ticket": ticket_id, "detail": texte},
        )

    async def _emettre_succes(
        self,
        project_id: str,
        ticket_id: str,
        pr_number: int,
        on_event: EventCallback,
        pipeline_log_path: Path | None = None,
    ) -> None:
        """Emit ci_merge_done(merged=True) and record the success.

        With a `pipeline_log_path`, the merge is also written to the log.
        """
        self._resultats_merge[f"{project_id}:{ticket_id}"] = True
        ecrire_log_merge(pipeline_log_path, project_id, ticket_id, pr_number)
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
        await self._realigner_si_libre(project_id, ticket_id)

    async def _realigner_si_libre(self, project_id: str, ticket_id: str) -> None:
        """Fast-forward the local base unless a run holds the project (ticket-422).

        Après l'événement : un échec ou une lenteur du réalignement ne change
        rien au merge, déjà annoncé.
        """
        cible = self._realignements.get(f"{project_id}:{ticket_id}")
        if cible is None:
            return
        if RUN_REGISTRY.projet_occupe(project_id):
            _logger.info(
                "realignement_ignore",
                extra={"project": project_id, "raison": "un run occupe le projet"},
            )
            return
        await realigner_base(cible.racine, cible.base_branch, project_id)

    async def _pr_mergee(self, etat_pr: EtatPr | None, pr_number: int) -> bool:
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

    async def _succes_malgre_erreur_reseau(
        self,
        project_id: str,
        ticket_id: str,
        pr_number: int,
        exc: BaseException,
        on_event: EventCallback,
        pipeline_log_path: Path | None,
    ) -> None:
        """The PR is merged although the network call failed: a success."""
        ecrire_ligne_log(
            pipeline_log_path,
            ticket_id,
            f"livraison: PR #{pr_number} mergée malgré une erreur réseau "
            f"({decrire_exception(exc)})",
        )
        await self._emettre_succes(project_id, ticket_id, pr_number, on_event)

#: Instance partagée par tous les routeurs. Un singleton en mémoire suffit
#: pour un backend local (ADR-038).
CI_WATCHER = CIWatcher()
