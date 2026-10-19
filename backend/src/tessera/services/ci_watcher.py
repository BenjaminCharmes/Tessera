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

Shutdown: call arreter() to cancel all running tasks without raising exceptions.
"""
import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx

from tessera.models.ticket import TicketStatus
from tessera.services.livraison import Livraison
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

#: Relit le SHA de tête d'une PR ; `None` quand il ne peut pas être connu.
TetePr = Callable[[int], Awaitable[str | None]]


#: Dit si le premier SHA est un ancêtre du second : `True`, `False`, ou `None`
#: quand l'ascendance ne peut pas se vérifier (commit inconnu localement…).
EstAncetre = Callable[[str, str], Awaitable[bool | None]]

#: Fenêtre de relecture par défaut : 4 relectures espacées de 15 s, soit
#: 5 lectures sur 60 s en comptant la première (ticket-527).
_RELECTURES_TETE = 4
_INTERVALLE_RELECTURE_TETE_S = 15.0


@dataclass(frozen=True)
class ControleTete:
    """What the watcher checks before merging: the PR head is the pushed commit.

    `pushed_sha` is `None` when the delivery could not record it — the watcher
    then refuses to merge (ticket-492).

    GitHub may still show the previous commit a few seconds after a push. When
    the head read is an ancestor of `pushed_sha` — or when that cannot be
    checked — the head is read again up to `relectures` times, `intervalle_s`
    apart, before the merge is refused (ticket-527). A head that is not an
    ancestor refuses at once.
    """

    pushed_sha: str | None
    lire_tete: TetePr
    est_ancetre: EstAncetre | None = None
    relectures: int = _RELECTURES_TETE
    intervalle_s: float = _INTERVALLE_RELECTURE_TETE_S


def decrire_exception(exc: BaseException) -> str:
    """Name the exception type, then its text when it has one."""
    texte = str(exc)
    nom = type(exc).__name__
    return f"{nom}: {texte}" if texte else nom


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
        # Réalignement de la base demandé par surveiller (ticket-422).
        # Clé : "project_id:ticket_id".
        self._realignements: dict[str, Realignement] = {}
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
        etat_pr: EtatPr | None = None,
        realignement: Realignement | None = None,
        controle_tete: ControleTete | None = None,
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
                pipeline_log_path, etat_pr, controle_tete,
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
    ) -> None:
        sem = self._semaphore_du_projet(project_id)
        try:
            async with sem:
                arret_erreur: str | None = None
                try:
                    await asyncio.wait_for(
                        self._livrer_et_emettre(
                            project_id, ticket_id, pr_number, livraison_phase_2,
                            on_event, pipeline_log_path, controle_tete,
                        ),
                        timeout=self._timeout_phase2_s,
                    )
                except asyncio.TimeoutError:
                    arret_erreur = f"délai dépassé ({self._timeout_phase2_s:.0f}s)"
                    _logger.warning(
                        "ci_watcher_timeout",
                        extra={"project": project_id, "ticket": ticket_id},
                    )
                except httpx.TransportError as exc:
                    # Une réponse perdue ne dit pas que l'action a échoué : on
                    # relit la PR avant de conclure (ticket-405).
                    if await self._pr_mergee(etat_pr, pr_number):
                        await self._succes_malgre_erreur_reseau(
                            project_id, ticket_id, pr_number, exc, on_event,
                            pipeline_log_path,
                        )
                    else:
                        arret_erreur = (
                            f"erreur inattendue : {decrire_exception(exc)}"
                        )
                        _logger.exception(
                            "ci_watcher_error",
                            extra={"project": project_id, "ticket": ticket_id},
                        )
                except Exception as exc:  # noqa: BLE001
                    arret_erreur = f"erreur inattendue : {decrire_exception(exc)}"
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
            self._realignements.pop(cle, None)
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
        controle_tete: ControleTete | None = None,
    ) -> None:
        arret_tete = await self._tete_changee(controle_tete, pr_number)
        if arret_tete is not None:
            # La branche a bougé depuis le push : ce qui serait mergé n'est pas
            # ce que le reviewer a lu. La PR reste ouverte (ticket-492).
            await self._emettre_echec(
                project_id, ticket_id, pr_number, arret_tete, on_event,
                pipeline_log_path,
            )
            return
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
            await self._emettre_succes(
                project_id, ticket_id, pr_number, on_event, pipeline_log_path
            )

    async def _tete_changee(
        self, controle: ControleTete | None, pr_number: int
    ) -> str | None:
        """The stop line when the PR head is not the pushed commit, else None.

        Fails closed (ADR-039): an unknown pushed commit, an unreadable head or
        a missing one all refuse the merge.
        """
        if controle is None:
            return None
        if controle.pushed_sha is None:
            return (
                f"commit poussé inconnu : la PR #{pr_number} n'est pas mergée, "
                "elle reste ouverte"
            )
        tete, arret = await self._lire_tete(controle, pr_number)
        if tete is None:
            return arret
        if tete == controle.pushed_sha:
            return None
        if not await self._tete_en_retard(controle, controle.pushed_sha, tete):
            return self._arret_tete_changee(pr_number, tete, controle.pushed_sha)
        # Une tête en retard n'est pas une tête changée : GitHub rattrape le
        # push. On relit sur la fenêtre, sans jamais merger une autre tête.
        for _ in range(controle.relectures):
            await asyncio.sleep(controle.intervalle_s)
            tete, arret = await self._lire_tete(controle, pr_number)
            if tete is None:
                return arret
            if tete == controle.pushed_sha:
                return None
        return self._arret_tete_changee(pr_number, tete, controle.pushed_sha)

    async def _lire_tete(
        self, controle: ControleTete, pr_number: int
    ) -> tuple[str | None, str | None]:
        """Read the PR head: `(sha, None)`, or `(None, stop line)` when unknown."""
        try:
            tete = await controle.lire_tete(pr_number)
        except Exception as exc:  # noqa: BLE001 — une tête illisible refuse le merge
            return None, (
                f"tête de la PR #{pr_number} illisible "
                f"({decrire_exception(exc)}) : elle reste ouverte"
            )
        if tete is None:
            return None, f"tête de la PR #{pr_number} inconnue : elle reste ouverte"
        return tete, None

    async def _tete_en_retard(
        self, controle: ControleTete, pushed_sha: str, tete: str
    ) -> bool:
        """True when `tete` may just be behind `pushed_sha` and is worth re-reading.

        Fails towards waiting, never towards merging: an ancestry that cannot be
        checked only delays the refusal (ADR-039).
        """
        if controle.est_ancetre is None:
            return True
        try:
            ancetre = await controle.est_ancetre(tete, pushed_sha)
        except Exception as exc:  # noqa: BLE001 — ascendance invérifiable : on relit
            _logger.warning(
                "ci_watcher_ascendance_illisible",
                extra={"erreur": decrire_exception(exc)},
            )
            return True
        return ancetre is None or ancetre

    def _arret_tete_changee(self, pr_number: int, tete: str, pushed_sha: str) -> str:
        return (
            f"la tête de la PR #{pr_number} n'est plus le commit poussé : "
            f"{tete[:7]} au lieu de {pushed_sha[:7]}. "
            "La PR reste ouverte."
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
        self._ecrire_log_merge(pipeline_log_path, project_id, ticket_id, pr_number)
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
        self._ecrire_ligne_log(
            pipeline_log_path,
            ticket_id,
            f"livraison: PR #{pr_number} mergée malgré une erreur réseau "
            f"({decrire_exception(exc)})",
        )
        await self._emettre_succes(project_id, ticket_id, pr_number, on_event)

    def _ecrire_log_blocage(
        self,
        pipeline_log_path: Path | None,
        ticket_id: str,
        pr_number: int,
        arret: str,
    ) -> None:
        """Write a blocking delivery entry to the pipeline log."""
        self._ecrire_ligne_log(
            pipeline_log_path,
            ticket_id,
            f"livraison: arrêt — PR #{pr_number} non mergée : {arret[:200]}",
        )

    def _ecrire_ligne_log(
        self,
        pipeline_log_path: Path | None,
        ticket_id: str,
        message: str,
    ) -> None:
        """Append one timestamped line for `ticket_id` to the pipeline log."""
        if pipeline_log_path is None:
            return
        self._ajouter_au_log(pipeline_log_path, f"[{ticket_id}] {message}")

    def _ecrire_log_merge(
        self,
        pipeline_log_path: Path | None,
        project_id: str,
        ticket_id: str,
        pr_number: int,
    ) -> None:
        """Append `[project] ticket PR #N mergée (CI verte)` to the pipeline log."""
        self._ajouter_au_log(
            pipeline_log_path,
            f"[{project_id}] {ticket_id} PR #{pr_number} mergée (CI verte)",
        )

    def _ajouter_au_log(self, pipeline_log_path: Path | None, texte: str) -> None:
        """Append one timestamped line to the pipeline log; never raises."""
        if pipeline_log_path is None:
            return
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        line = f"- {ts} — {texte}\n"
        try:
            pipeline_log_path.parent.mkdir(parents=True, exist_ok=True)
            with pipeline_log_path.open("a", encoding="utf-8") as f:
                f.write(line)
        except Exception as exc:  # noqa: BLE001
            _logger.warning("pipeline_log_write_failed", extra={"error": str(exc)})

#: Instance partagée par tous les routeurs. Un singleton en mémoire suffit
#: pour un backend local (ADR-038).
CI_WATCHER = CIWatcher()
