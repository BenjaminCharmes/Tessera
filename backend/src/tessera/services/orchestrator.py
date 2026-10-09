"""Pipeline orchestration — the sequence only.

Each stage lives in `pipeline_stages.py`; this module chains them and owns
the early exits. Keeping the flow readable in one screen is the point: the
order of the stages, and the conditions that end a run, are the part that is
hard to get right.
"""
import asyncio
import time
from datetime import datetime, timezone
from pathlib import Path
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, Optional

from tessera.models.agent import AgentConfig, AgentRole
from tessera.models.ticket import Ticket, TicketPriority, TicketStatus
from tessera.services.agent_runner import AgentRunner
from tessera.services.dialogue import DialogueChannel
from tessera.services.providers.enregistrant import activer_enregistrement
from tessera.services.livraison import Livraison
from tessera.services.pipeline_events import (
    EventCallback,
    EventType,
    OrchestratorEvent,
    PipelineResult,
)
from tessera.services.ticket_service import TicketService
from tessera.utils.logger import get_logger

from tessera.services import pipeline_outcomes as outcomes
from tessera.services import pipeline_stages as stages
from tessera.services.pipeline_run import PipelineRun, set_status, tolerant
from tessera.services.pipeline_plan import run_plan

if TYPE_CHECKING:
    from tessera.services.carte_du_depot import CarteDuDepot
    from tessera.services.quota_tracker import QuotaTracker
    from tessera.services.run_recorder import RunRecorder
    from tessera.services.git_workspace import GitWorkspaceService
    from tessera.services.security_auditor import SecurityAuditorService
    from tessera.services.test_runner import TestRunnerService
    from tessera.services.validator import ValidatorService

_logger = get_logger(__name__)

_PRIORITY_ORDER: dict[TicketPriority, int] = {
    TicketPriority.critical: 0,
    TicketPriority.high: 1,
    TicketPriority.medium: 2,
    TicketPriority.low: 3,
}


class Orchestrator:
    def __init__(
        self,
        runner: AgentRunner,
        ticket_service: TicketService,
        project_context: str,
        agent_configs: list[AgentConfig],
        pipeline_log_path: Path,
        max_review_rounds: int = 3,
        test_runner: Optional["TestRunnerService"] = None,
        test_command: Optional[str] = None,
        security_auditor: Optional["SecurityAuditorService"] = None,
        validator: Optional["ValidatorService"] = None,
        project_path: Optional[Path] = None,
        git_workspace: Optional["GitWorkspaceService"] = None,
        run_max_budget_usd: float = 0.0,
        quota_tracker: Optional["QuotaTracker"] = None,
        livrer: Optional[Callable[[PipelineResult], Awaitable["Livraison"]]] = None,
        documenter: Optional[Callable[[], Awaitable[Any]]] = None,
        run_recorder: Optional["RunRecorder"] = None,
        carte_du_depot: Optional["CarteDuDepot"] = None,
        surveiller: Optional[
            Callable[[str, str, int, "EventCallback"], Awaitable[None]]
        ] = None,
        ci_watcher: Optional[Any] = None,
        base_branch: Optional[str] = None,
        merge_without_ci: bool = False,
        attente_merge_max_s: float = 600.0,
    ) -> None:
        self._runner = runner
        self._ticket_svc = ticket_service
        self._project_context = project_context
        self._agent_configs = agent_configs
        self._log_path = pipeline_log_path
        self._max_review_rounds = max_review_rounds
        self._test_runner = test_runner
        self._test_command = test_command
        self._security_auditor = security_auditor
        self._validator = validator
        self._project_path = project_path
        self._git_workspace = git_workspace
        self._run_max_budget_usd = run_max_budget_usd
        self._spent_usd = 0.0
        # Le quota d'abonnement est la ressource réellement finie en mode
        # `agent_sdk` : la dépense estimée de ticket-052 ne la mesure pas.
        self._quota_tracker = quota_tracker
        # Ce que devient le commit d'un run approuvé — poussé, mis en PR,
        # mergé. L'orchestrateur ne sait pas ce que ça veut dire : il appelle,
        # le routeur décide. C'est ce qui le garde ignorant de GitHub, et ce
        # qui met la livraison sur **tous** les modes de run (ticket-084).
        self._livrer = livrer
        # La documentation se met à jour **une fois par lot**, à la fin d'une
        # file ou d'un run autonome — jamais par ticket. Elle décrit le
        # produit, pas un changement : trois tickets sur une même feature
        # produiraient trois réécritures partielles du même fichier
        # (ticket-092).
        self._documenter = documenter
        # Ouvre et clôt la ligne d'un run en base quand l'appelant n'en a pas
        # fourni : la file, le run autonome et le chat ne persistaient ni
        # leurs runs ni les coûts de leurs appels (ticket-121).
        self._run_recorder = run_recorder
        # La liste des fichiers suivis, donnée au codeur au premier tour pour
        # qu'il ne la reconstruise pas à coups de `Glob` (ticket-190).
        self._carte_du_depot = carte_du_depot
        # Confie la phase 2 (attente CI + merge) à `CIWatcher`, sans attendre
        # (ADR-051). Appelé seulement quand la phase 1 a ouvert une PR.
        self._surveiller = surveiller
        # Permet à `run_queue` de savoir quels tickets attendent leur CI,
        # et d'attendre leur merge avant de démarrer un ticket dépendant.
        self._ci_watcher = ci_watcher
        # La branche de base du projet — utilisée pour y revenir après livraison
        # (ticket-378). None quand l'orchestrateur tourne sans git workspace.
        self._base_branch = base_branch
        # Sur un projet merge_without_ci: true, le merge suit la PR de quelques
        # secondes. La file attend ce signal avant de laisser le ticket suivant
        # créer sa branche, pour qu'il parte d'une base à jour (ticket-382).
        self._merge_without_ci = merge_without_ci
        # Durée maximale d'attente du merge en secondes. Passé ce délai, la file
        # continue sans réalignement plutôt que de bloquer indéfiniment.
        self._attente_merge_max_s = attente_merge_max_s

    @property
    def quota(self) -> Optional["QuotaTracker"]:
        return self._quota_tracker

    @property
    def spent_usd(self) -> float:
        """Cumulative spend since this orchestrator was built."""
        return round(self._spent_usd, 10)

    def record_spend(self, cost_usd: float) -> None:
        """Add one agent call's cost to the run's running total."""
        self._spent_usd += cost_usd or 0.0

    def budget_exhausted(self) -> bool:
        """True once the run has spent its ceiling. `0` means no ceiling."""
        if self._run_max_budget_usd <= 0:
            return False
        return self._spent_usd >= self._run_max_budget_usd

    def _config_for(self, role: AgentRole) -> Optional[AgentConfig]:
        return next((c for c in self._agent_configs if c.role == role.value), None)

    async def run_pipeline(
        self,
        project_id: str,
        ticket_id: str,
        on_event: EventCallback,
        run_id: str | None = None,
        dialogue: DialogueChannel | None = None,
        envelope_run_id: str | None = None,
    ) -> PipelineResult:
        """Mène le ticket, puis livre son travail si le projet le permet.

        La livraison est ici, et non chez l'appelant, parce que `run_queue` et
        `run_autonomous` passent tous deux par cette méthode : la brancher
        ailleurs la réserverait au run unique, alors que c'est en file que
        l'absence de clic compte le plus.

        ``envelope_run_id`` est l'identifiant de la ligne enveloppe créée par
        ``executer`` pour un run en file ou autonome. Il est transmis à
        ``RunRecorder`` pour lier la ligne par-ticket à son enveloppe
        (ticket-280).
        """
        on_event = tolerant(on_event)
        resultat = await self._run_enregistre(
            project_id, ticket_id, on_event,
            run_id=run_id, dialogue=dialogue,
            envelope_run_id=envelope_run_id,
        )
        if not resultat.approved:
            return resultat

        # La documentation part sur la branche du run, avant sa livraison :
        # elle décrit ce que la PR livre, et se relit avec (ticket-198).
        # Exception : les tickets légers (ticket-292) ne déclenchent pas de
        # mise à jour immédiate — le marqueur ne bouge pas, et le prochain
        # ticket normal documente le lot entier, léger compris.
        ticket_approuve = await self._ticket_svc.get_ticket(ticket_id)
        if ticket_approuve is None or not ticket_approuve.light:
            await self._documenter_le_run(resultat, on_event)

        if self._livrer is None:
            return resultat

        await on_event(
            OrchestratorEvent(
                type=EventType.LIVRAISON_STARTED,
                ticket_id=ticket_id,
            )
        )
        # Phase 1 seulement : rebase, push, PR. La phase 2 (attente CI + merge)
        # est confiée à `CIWatcher` en tâche de fond (ADR-051). Le verrou
        # (ADR-038) se libère dès que `run_pipeline` rend la main, c'est-à-dire
        # dès la PR ouverte — pas après le merge.
        livraison = await self._livrer(resultat)
        for etape, duree_ms in zip(livraison.etapes, livraison.durees_ms):
            self._log(f"[{ticket_id}] livraison: {etape} ({duree_ms:.0f}ms)")
        if livraison.arret:
            self._log(f"[{ticket_id}] livraison: arrêt — {livraison.arret[:100]}")
        # Commit the delivery log lines just written, then return to the base
        # branch so the working tree is clean after a delivered run (ticket-378).
        await self._finaliser_livraison(livraison)
        await on_event(
            OrchestratorEvent(
                type=EventType.LIVRAISON_DONE,
                ticket_id=ticket_id,
                data=livraison.__dict__,
            )
        )
        # Si la phase 1 a ouvert une PR sans conflit, confier la phase 2 au
        # CIWatcher : il attend la CI et merge en arrière-plan. `surveiller`
        # retourne immédiatement (crée une tâche asyncio), ce qui permet à
        # `run_pipeline` de rendre la main et au verrou de se libérer avant
        # que `ci_merge_done` soit émis.
        if (
            livraison.pr_number is not None
            and livraison.arret is None
            and self._surveiller is not None
        ):
            await self._surveiller(project_id, ticket_id, livraison.pr_number, on_event)

        return resultat.model_copy(update={"livraison": livraison})

    async def _run_enregistre(
        self,
        project_id: str,
        ticket_id: str,
        on_event: EventCallback,
        run_id: str | None,
        dialogue: DialogueChannel | None,
        envelope_run_id: str | None = None,
    ) -> PipelineResult:
        """Run the pipeline inside a database record, when nobody opened one.

        Clore appartient à celui qui a ouvert : un `run_id` fourni par
        l'appelant — `/orchestrator/run`, le stream single — est le sien, il
        y rattache ses événements et le clôt lui-même. La ligne se ferme
        aussi quand le run lève : c'est ce qu'ADR-037 demande au routeur, et
        la file n'a pas de routeur par ticket pour le faire.
        """
        if run_id is not None or self._run_recorder is None:
            return await self._run_pipeline(
                project_id, ticket_id, on_event, run_id=run_id, dialogue=dialogue
            )
        run_id = await self._run_recorder.ouvrir(
            project_id, ticket_id, parent_run_id=envelope_run_id
        )
        resultat: PipelineResult | None = None
        try:
            resultat = await self._run_pipeline(
                project_id, ticket_id, on_event, run_id=run_id, dialogue=dialogue
            )
            return resultat
        finally:
            await self._run_recorder.clore(run_id, resultat)

    async def _run_pipeline(
        self,
        project_id: str,
        ticket_id: str,
        on_event: EventCallback,
        run_id: str | None = None,
        dialogue: DialogueChannel | None = None,
    ) -> PipelineResult:
        ticket = await self._ticket_svc.get_ticket(ticket_id)
        if ticket is None and self._git_workspace is not None:
            # Le fichier ticket a pu être déplacé sans commit lors d'un run
            # précédent coupé net (ex: blocked/ sans commit). On tente de le
            # retrouver sur la base distante avant de conclure « introuvable ».
            restored = await self._git_workspace.restaurer_ticket_depuis_base(ticket_id)
            if restored:
                ticket = await self._ticket_svc.get_ticket(ticket_id)
        if ticket is None:
            raise ValueError(f"Ticket introuvable : {ticket_id}")

        # Sans canal branché — appel programmatique, test, run autonome — le
        # run reste non interactif : il ne doit jamais se suspendre en
        # attendant une réponse que personne ne viendra donner (ticket-066).
        run = PipelineRun(
            project_id=project_id,
            ticket=ticket,
            on_event=on_event,
            run_id=run_id,
            dialogue=dialogue or DialogueChannel(interactive=False),
        )

        # Active l'enregistrement des appels LLM dans `agent_calls` pour la
        # durée de ce ticket. Tous les providers enveloppés dans
        # `ProviderEnregistrant` lisent ces variables de contexte (ticket-211).
        activer_enregistrement(run.run_id, run.ticket_id)

        refused = await stages.ensure_clean_tree(self, run)
        if refused is not None:
            return refused

        refused = await stages.create_branch(self, run)
        if refused is not None:
            return refused
        stages.take_artifact_snapshot(self, run)
        await set_status(self, run, TicketStatus.in_progress)
        run.carte_du_depot = await self._carte()
        # Avant le premier tour, et seulement si le ticket le déclare. Ne lève
        # jamais : un plan manqué laisse le run tel qu'avant ticket-243.
        await run_plan(self, run)

        # À partir d'ici une branche existe et les agents écrivent sur disque :
        # une panne qui remonterait laisserait leur travail non commité, donc
        # l'arbre sale et la file bloquée (ADR-018). C'est ce qui est arrivé au
        # premier run réel du ticket-101, coupé par un plafond du SDK au milieu
        # d'un tour. On rend un run non approuvé, jamais une erreur serveur —
        # le raisonnement d'ADR-030 pour la livraison, appliqué à la production.
        try:
            return await self._run_rounds(run, ticket_id)
        except Exception as exc:  # noqa: BLE001 — la cause part dans le résultat
            return await outcomes.finish_interrupted(self, run, exc)

    async def _carte(self) -> str:
        """The repository map, or nothing: an aid must never cost the run."""
        if self._carte_du_depot is None:
            return ""
        try:
            return await self._carte_du_depot.rendre()
        except Exception as exc:  # noqa: BLE001 — une carte absente n'arrête rien
            _logger.warning("carte_du_depot_failed", extra={"error": str(exc)})
            return ""

    async def _run_rounds(self, run: PipelineRun, ticket_id: str) -> PipelineResult:
        """Enchaîne les tours de revue jusqu'à approbation, blocage ou épuisement."""
        for round_num in range(1, self._max_review_rounds + 1):
            # Le plafond du run se vérifiait entre deux tickets seulement : un
            # ticket seul pouvait le dépasser de plus du double sur trois tours
            # (ticket-191). Un tour 1 démarre toujours — refuser un ticket est
            # le rôle de la vérification entre tickets, pas de celle-ci.
            if round_num > 1 and self.budget_exhausted():
                return await outcomes.finish_budget_exhausted(self, run)

            run.start_round(round_num)
            context = stages.build_context(self, run)

            # L'arrêt est vérifié **entre** les étapes, jamais au milieu de
            # l'une : couper un agent en plein tour jetterait un travail déjà
            # payé, et laisserait le diff dans un état que personne n'a relu.
            if run.stop_requested:
                return await outcomes.finish_stopped(self, run)

            await stages.run_coder(self, run, context)

            if run.stop_requested:
                return await outcomes.finish_stopped(self, run)

            # Une suite rouge renvoie au codeur sans passer par la revue :
            # un reviewer n'a pas à arbitrer un fait déjà établi, et l'appel
            # est économisé (ticket-098).
            # Deux expirations de suite terminent le run en blocked sans
            # repasser par le codeur (ticket-349).
            tests_result = await stages.run_tests(self, run)
            if not isinstance(tests_result, bool):
                return tests_result
            if not tests_result:
                run.review_feedback.append(_echec_de_tests(run))
                self._log(f"[{ticket_id}] tests rouges au tour {round_num}")
                continue

            blocked = await stages.run_security_audit(self, run)
            if blocked is not None:
                return blocked

            if run.stop_requested:
                return await outcomes.finish_stopped(self, run)

            # Reviewer et validateur tournent en parallèle — la sécurité leur
            # est commune, mais aucun ne dépend de l'autre (ticket-289).
            (rev_approved, rev_reason, raw_verdict), (val_approved, val_reason) = (
                await asyncio.gather(
                    stages.run_review(self, run, context),
                    stages.run_validation(self, run),
                )
            )

            approved = rev_approved and val_approved
            if approved:
                return await outcomes.finish_approved(self, run)

            # Nommer l'auteur quand les deux refusent : le codeur voit un seul
            # feedback au tour suivant, et il doit savoir qui objecte quoi.
            feedback_parts: list[str] = []
            if not rev_approved:
                rev_feedback = rev_reason or raw_verdict[:500]
                feedback_parts.append(f"Reviewer : {rev_feedback}")
            if not val_approved:
                feedback_parts.append(f"Validateur : {val_reason}")
            feedback = "\n\n".join(feedback_parts) if feedback_parts else raw_verdict[:500]

            run.review_feedback.append(feedback)
            self._log(
                f"[{ticket_id}] CHANGES_REQUESTED tour {round_num}: {feedback[:100]}"
            )

        return await outcomes.finish_rounds_exhausted(self, run)

    async def pick_next_ticket(self, project_id: str) -> Optional[Ticket]:
        todos = await self._ticket_svc.list_tickets(status=TicketStatus.todo)
        done_ids = {
            t.id for t in await self._ticket_svc.list_tickets(status=TicketStatus.done)
        }
        eligible = [t for t in todos if all(dep in done_ids for dep in t.depends_on)]
        if not eligible:
            return None
        return min(eligible, key=lambda t: _PRIORITY_ORDER.get(t.priority, 99))

    async def _est_termine(self, ticket_id: str) -> bool:
        """Le ticket est-il déjà `done` ou `cancelled` ?

        Un ticket introuvable n'est pas « terminé » : le laisser passer rend
        l'erreur au bon endroit, dans `_run_pipeline`, qui sait la nommer.
        """
        ticket = await self._ticket_svc.get_ticket(ticket_id)
        if ticket is None:
            return False
        return ticket.status in (TicketStatus.done, TicketStatus.cancelled)

    async def run_queue(
        self,
        project_id: str,
        ticket_ids: list[str],
        on_event: EventCallback | None = None,
        dialogue: "DialogueChannel | None" = None,
        envelope_run_id: str | None = None,
        budget_override_usd: float | None = None,
    ) -> list[PipelineResult]:
        """Enchaîne une sélection de tickets, dans l'ordre demandé.

        Distinct de `run_autonomous`, qui choisit lui-même le prochain ticket :
        ici l'utilisateur a désigné un lot et son ordre.

        **Un ticket non approuvé arrête la file.** Les tickets d'un lot
        dépendent presque toujours les uns des autres — c'est le découpage que
        produit le planificateur — et enchaîner sur une base que personne n'a
        validée ferait travailler le suivant sur un état douteux. Mieux vaut
        s'arrêter net et laisser décider.

        En mode file, le plafond de dépense vaut `run_max_budget_usd × nombre
        de tickets` par défaut — un plafond pensé pour un ticket seul ne doit
        pas arrêter une file de quinze (ticket-383). ``budget_override_usd``
        remplace ce calcul quand la requête fixe explicitement un budget.
        """
        # Plafond effectif pour l'ensemble de la file : on multiplie le plafond
        # par ticket par le nombre de tickets, sauf si la requête en fixe un
        # autre. 0 signifie « pas de plafond » (même sémantique que
        # `run_max_budget_usd`).
        if budget_override_usd is not None:
            effective_budget = budget_override_usd
        elif self._run_max_budget_usd > 0:
            effective_budget = self._run_max_budget_usd * len(ticket_ids)
        else:
            effective_budget = 0.0

        async def _noop(event: OrchestratorEvent) -> None:
            pass

        callback = tolerant(on_event or _noop)
        results: list[PipelineResult] = []

        for index, ticket_id in enumerate(ticket_ids, start=1):
            # Comme pour le budget et le quota, on vérifie **entre** deux
            # tickets : s'arrêter au milieu de l'un laisserait son travail non
            # commité (ADR-018, ADR-020).
            if dialogue is not None and dialogue.stop_requested:
                self._log(f"[{project_id}] file interrompue : arrêt demandé")
                break
            if effective_budget > 0 and self._spent_usd >= effective_budget:
                self._log(f"[{project_id}] file interrompue : plafond de dépense")
                await callback(
                    OrchestratorEvent(
                        type=EventType.QUEUE_PROGRESS,
                        ticket_id=ticket_id,
                        data={
                            "raison": "budget",
                            "index": index,
                            "total": len(ticket_ids),
                            "restants": list(ticket_ids[index - 1 :]),
                            "faits": list(ticket_ids[: index - 1]),
                            "spent_usd": self._spent_usd,
                            "budget_usd": effective_budget,
                        },
                    )
                )
                break

            # Un ticket déjà terminé se **saute**, il ne s'exécute pas : le
            # relancer refait un travail livré, sur une branche neuve et aux
            # frais du quota. L'UI cachait déjà le bouton « Lancer » sur un
            # `done`, mais pas celui de la file, et rien ne rattrapait ici —
            # or cet endpoint est appelable directement (ticket-115).
            #
            # Sauter plutôt qu'arrêter : une file où un ticket terminé s'est
            # glissé doit traiter les autres.
            if await self._est_termine(ticket_id):
                self._log(f"[{project_id}] {ticket_id} sauté : déjà terminé")
                continue

            await callback(
                OrchestratorEvent(
                    type=EventType.QUEUE_PROGRESS,
                    ticket_id=ticket_id,
                    # `restants` et pas seulement l'index : savoir qu'on est
                    # au deuxième de trois ne dit pas lesquels attendent, ce
                    # qui est l'information utile quand on envisage
                    # d'interrompre la file (ticket-172).
                    data={
                        "index": index,
                        "total": len(ticket_ids),
                        "restants": list(ticket_ids[index:]),
                        "faits": list(ticket_ids[: index - 1]),
                    },
                )
            )

            result = await self.run_pipeline(
                project_id, ticket_id, callback, dialogue=dialogue,
                envelope_run_id=envelope_run_id,
            )
            results.append(result)

            if not result.approved:
                self._log(
                    f"[{project_id}] file interrompue : {ticket_id} non approuvé"
                )
                break

            # Si la PR de ce ticket est ouverte et attend la CI :
            # — avec CIWatcher (ADR-051) : attendre le merge pour les tickets
            #   dépendants, laisser les indépendants démarrer.
            # — sans CIWatcher (compatibilité) : arrêter la file si le ticket
            #   suivant dépend de celui-ci, comme avant ticket-307.
            if (
                result.livraison is not None
                and result.livraison.pr_number is not None
            ):
                restants = ticket_ids[index:]
                if self._ci_watcher is not None:
                    if self._merge_without_ci and restants:
                        # merge_without_ci : attendre le merge pour TOUS les
                        # tickets suivants, qu'ils en dépendent ou non — puis
                        # réaligner la base distante avant la création de la
                        # branche du ticket suivant (ticket-382).
                        # Sans ticket restant, l'attente n'apporte rien.
                        await self._attendre_merge_et_syncer(project_id, ticket_id)
                    else:
                        stop = await _attendre_si_dependant(
                            self._ticket_svc,
                            self._ci_watcher,
                            project_id,
                            ticket_id,
                            restants,
                        )
                        if stop:
                            self._log(
                                f"[{project_id}] file interrompue : {ticket_id} non mergé"
                            )
                            break
                        self._log(
                            f"[{project_id}] {ticket_id} PR #{result.livraison.pr_number}"
                            " confiée au CIWatcher"
                        )
                else:
                    livraison_bloquee = await _trouver_bloquant(
                        self._ticket_svc,
                        ticket_id,
                        result.livraison.pr_number,
                        restants,
                    )
                    if livraison_bloquee is not None:
                        results[-1] = results[-1].model_copy(
                            update={"livraison": livraison_bloquee}
                        )
                        break
            else:
                # Approuvé mais sans PR : si un ticket restant dépend de
                # celui-ci, son travail n'est pas sur la base — il partirait
                # d'un état qui ne contient pas la dépendance. On arrête la
                # file plutôt que de laisser ce ticket produire du travail à
                # jeter (ticket-361).
                restants = ticket_ids[index:]
                livraison_bloquee = await _trouver_bloquant_sans_pr(
                    self._ticket_svc,
                    ticket_id,
                    result.livraison,
                    restants,
                )
                if livraison_bloquee is not None:
                    results[-1] = results[-1].model_copy(
                        update={"livraison": livraison_bloquee}
                    )
                    self._log(
                        f"[{project_id}] file interrompue : {ticket_id}"
                        " n'a pas été livré"
                    )
                    break

        return results

    async def run_autonomous(
        self,
        project_id: str,
        max_tickets: int = 5,
        on_event: EventCallback | None = None,
        envelope_run_id: str | None = None,
    ) -> list[PipelineResult]:
        async def _noop(event: OrchestratorEvent) -> None:
            pass

        callback = tolerant(on_event or _noop)
        results: list[PipelineResult] = []

        for _ in range(max_tickets):
            # Le plafond est vérifié *entre* les tickets : interrompre un
            # ticket en cours laisserait son travail non commité, ce que
            # l'isolation par branche interdit (ADR-018).
            if self.budget_exhausted():
                _logger.warning(
                    "run_budget_exhausted",
                    extra={
                        "spent_usd": self.spent_usd,
                        "max_usd": self._run_max_budget_usd,
                    },
                )
                self._log(
                    f"[{project_id}] run interrompu : {self.spent_usd:.2f} USD "
                    f"dépensés sur {self._run_max_budget_usd:.2f} autorisés"
                )
                break

            # Seconde condition d'arrêt : le quota réel de l'abonnement. Un
            # quota inconnu ne bloque pas — un provider muet doit rester
            # indiscernable d'un quota confortable (ticket-054).
            if self._quota_tracker is not None and self._quota_tracker.is_low():
                snapshot = self._quota_tracker.snapshot
                _logger.warning(
                    "run_quota_low",
                    extra={"utilization": snapshot.utilization if snapshot else None},
                )
                self._log(
                    f"[{project_id}] run interrompu : quota d'abonnement à "
                    f"{(snapshot.utilization * 100) if snapshot else 0:.0f} %"
                )
                await callback(
                    OrchestratorEvent(
                        type=EventType.QUOTA_UPDATED,
                        ticket_id="",
                        data={
                            **self._quota_tracker.as_event_data(),
                            "run_interrupted": True,
                        },
                    )
                )
                break

            ticket = await self.pick_next_ticket(project_id)
            if ticket is None:
                break
            result = await self.run_pipeline(
                project_id, ticket.id, callback,
                envelope_run_id=envelope_run_id,
            )
            results.append(result)

        return results

    async def _documenter_le_run(
        self, resultat: PipelineResult, on_event: EventCallback
    ) -> None:
        """Met à jour la documentation après un run approuvé, sur sa branche.

        Le lot reste celui du marqueur : un run qui suit cinq tickets non
        documentés les documente tous. La documentation est commitée ici, sur
        la branche du run, pour partir dans sa PR — à la fin d'une file, elle
        restait sur le disque sans commit, et le run suivant refusait l'arbre
        sale (ADR-018). Un échec ne casse pas le run : le travail est commité,
        et perdre son résultat pour une documentation en retard serait
        disproportionné (ticket-198).
        """
        if self._documenter is None:
            return
        await on_event(
            OrchestratorEvent(
                type=EventType.DOCUMENTATION_STARTED,
                ticket_id=resultat.ticket_id,
            )
        )
        t0 = time.monotonic()
        try:
            doc = await self._documenter()
        except Exception as exc:  # noqa: BLE001 — voir la docstring
            _logger.warning("documentation_echouee", extra={"erreur": str(exc)})
            self._log(
                f"[{resultat.ticket_id}] documentation: échec — {str(exc)[:80]}"
            )
            await on_event(
                OrchestratorEvent(
                    type=EventType.DOCUMENTATION_FAILED,
                    ticket_id=resultat.ticket_id,
                    data={"error": str(exc)},
                )
            )
            return
        doc_ms = int((time.monotonic() - t0) * 1000)
        fichiers = list(getattr(doc, "fichiers_modifies", []) or [])
        refus = list(getattr(doc, "refus", []) or [])
        # « 0 fichier(s) » seul cachait six refus d'affilée sur démineur, chacun
        # pour plusieurs minutes de calcul (ticket-342).
        motifs = "".join(f" — refusé : {r[:160]}" for r in refus)
        self._log(
            f"[{resultat.ticket_id}] documentation: {len(fichiers)} fichier(s)"
            f" ({doc_ms}ms){motifs}"
        )
        tickets = list(getattr(doc, "tickets", []) or [])
        tronque = bool(getattr(doc, "tronque", False))
        marqueur_ecrit = bool(getattr(doc, "marqueur_ecrit", False))
        # Commiter si des fichiers de doc ont changé **ou** si le marqueur a
        # été réécrit : dans les deux cas l'arbre doit rester propre avant la
        # livraison (ADR-018, ticket-213).
        if (fichiers or marqueur_ecrit) and self._git_workspace is not None and resultat.branch is not None:
            try:
                await self._git_workspace.commit_all(
                    f"docs: update documentation for {resultat.ticket_id}"
                )
            except Exception as exc:  # noqa: BLE001
                _logger.warning("documentation_commit_echoue", extra={"erreur": str(exc)})
                refus.append(f"commit : {exc}")
        if fichiers or refus or tronque:
            await on_event(
                OrchestratorEvent(
                    type=EventType.DOC_UPDATED,
                    ticket_id=resultat.ticket_id,
                    data={
                        "fichiers": fichiers,
                        "refus": refus,
                        "tickets": tickets,
                        "tronque": tronque,
                    },
                )
            )

    async def _attendre_merge_et_syncer(
        self,
        project_id: str,
        ticket_id: str,
    ) -> None:
        """Wait for the merge then realign the local base from the remote.

        Called from run_queue when merge_without_ci is True, for every
        subsequent ticket regardless of depends_on. A timeout logs a warning
        and lets the queue continue without sync — better a possible conflict
        (which resolveur-conflit can handle) than a frozen queue (ticket-382).
        """
        assert self._ci_watcher is not None
        try:
            merged = await asyncio.wait_for(
                self._ci_watcher.attendre_merge(project_id, ticket_id),
                timeout=self._attente_merge_max_s,
            )
        except asyncio.TimeoutError:
            self._log(
                f"[{project_id}] {ticket_id} : délai d'attente du merge dépassé"
                f" ({self._attente_merge_max_s:.0f}s) — ticket suivant sans réalignement"
            )
            return

        if not merged:
            return

        if self._git_workspace is None or self._base_branch is None:
            return

        raison = await self._git_workspace.sync_base_depuis_distant(self._base_branch)
        if raison is not None:
            self._log(
                f"[{project_id}] {ticket_id} : réalignement de la base ignoré — {raison}"
            )
        else:
            self._log(
                f"[{project_id}] {ticket_id} : base réalignée sur {self._base_branch}"
            )

    async def _finaliser_livraison(self, livraison: "Livraison") -> None:
        """Commit delivery log lines and return to the base branch (ticket-378).

        Called after a successful delivery (PR opened). The log lines written
        just before this call are in ``pipeline-log.md`` but not yet committed;
        ``commit_bookkeeping`` picks them up so they appear in the last commit
        of the ticket branch.  Checking out the base branch then leaves the
        working tree clean, matching ADR-018.

        Errors are logged and swallowed: a failure here must not undo an
        already-opened PR.
        """
        if self._git_workspace is None or livraison.pr_number is None:
            return
        try:
            await self._git_workspace.commit_bookkeeping()
        except Exception as exc:  # noqa: BLE001
            _logger.warning("livraison_bookkeeping_failed", extra={"error": str(exc)})
        if self._base_branch is None:
            return
        try:
            await self._git_workspace.retourner_sur_base(self._base_branch)
        except Exception as exc:  # noqa: BLE001
            _logger.warning("livraison_checkout_base_failed", extra={"error": str(exc)})

    def _log(self, message: str) -> None:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        line = f"- {ts} — {message}\n"
        try:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
            with self._log_path.open("a", encoding="utf-8") as f:
                f.write(line)
        except Exception as exc:
            _logger.warning("pipeline_log_write_failed", extra={"error": str(exc)})


__all__ = [
    "EventCallback",
    "EventType",
    "Orchestrator",
    "OrchestratorEvent",
    "PipelineResult",
]


async def _attendre_si_dependant(
    ticket_svc: TicketService,
    ci_watcher: Any,
    project_id: str,
    ticket_id: str,
    restants: list[str],
) -> bool:
    """Await the CI merge for ``ticket_id`` if a remaining ticket depends on it.

    Walks ``restants`` to find the first ticket that declares ``ticket_id``
    in its ``depends_on``. When found, suspends until ``CIWatcher`` signals
    that ``ticket_id`` is no longer in the waiting set (merged or blocked).

    Returns True when the queue must stop (dependency not merged).
    Returns False when the queue may continue (no dependent, or merge succeeded).
    """
    for tid_dep in restants:
        ticket_dep = await ticket_svc.get_ticket(tid_dep)
        if ticket_dep is not None and ticket_id in ticket_dep.depends_on:
            merged = await ci_watcher.attendre_merge(project_id, ticket_id)
            return not merged
    return False


async def _trouver_bloquant(
    ticket_svc: TicketService,
    ticket_id: str,
    pr_number: int,
    restants: list[str],
) -> "Livraison | None":
    """Return a blocking Livraison when a remaining ticket depends on ``ticket_id``.

    Fallback used when CIWatcher is not wired (pre-ADR-051 deployments or
    tests that don't use the background watcher). When a dependent ticket is
    found, the returned livraison carries an ``arret`` that names the blocker;
    the caller stops the queue. Returns None when the queue may continue.
    """
    for tid_suivant in restants:
        ticket_suivant = await ticket_svc.get_ticket(tid_suivant)
        if ticket_suivant is not None and ticket_id in ticket_suivant.depends_on:
            return Livraison(
                arret=(
                    f"{tid_suivant} dépend de {ticket_id} "
                    f"dont la PR #{pr_number} n'est pas encore mergée."
                )
            )
    return None


async def _trouver_bloquant_sans_pr(
    ticket_svc: TicketService,
    ticket_id: str,
    livraison: "Livraison | None",
    restants: list[str],
) -> "Livraison | None":
    """Return a blocking Livraison when an approved-but-undelivered ticket has a dependent.

    Called when a ticket was approved but no PR was opened (livraison absent or
    pr_number is None).  Any remaining ticket that lists ticket_id in its
    depends_on cannot safely start from the current base without the approved
    changes.  Returns a Livraison whose arret names both the dependent and the
    undelivered ticket.  Returns None when no remaining ticket depends on
    ticket_id.
    """
    raison = (
        livraison.arret
        if livraison is not None and livraison.arret
        else "livraison non effectuée"
    )
    for tid_suivant in restants:
        ticket_suivant = await ticket_svc.get_ticket(tid_suivant)
        if ticket_suivant is not None and ticket_id in ticket_suivant.depends_on:
            return Livraison(
                arret=(
                    f"{tid_suivant} dépend de {ticket_id}, "
                    f"qui n'a pas été livré : {raison}"
                )
            )
    return None


def _echec_de_tests(run: "PipelineRun") -> str:
    """Ce que le codeur lit au tour suivant : le fait, puis les erreurs.

    Sans les erreurs, le second tour recommence à l'aveugle et produit
    souvent la même chose.
    """
    resultat = run.test_result
    if resultat is None:
        return "Les tests du projet ont échoué. Corrige-les avant toute chose."
    erreurs = "\n".join(resultat.errors[:10])
    return (
        "Les tests du projet échouent — corrige-les avant toute autre chose.\n"
        f"{resultat.output_summary}\n{erreurs}"
    )
