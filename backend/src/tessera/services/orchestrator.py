"""Pipeline orchestration — the sequence only.

Each stage lives in `pipeline_stages.py`; this module chains them and owns
the early exits. Keeping the flow readable in one screen is the point: the
order of the stages, and the conditions that end a run, are the part that is
hard to get right.
"""
import asyncio
from pathlib import Path
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, Optional

from tessera.models.agent import AgentConfig, AgentRole
from tessera.models.ticket import Ticket, TicketPriority, TicketStatus
from tessera.services.agent_runner import AgentRunner
from tessera.services.dialogue import DialogueChannel
from tessera.services.providers.enregistrant import activer_enregistrement
from tessera.services.journal_pipeline import ajouter_ligne
from tessera.services.livraison import Livraison
from tessera.services.attente_dependance import ids_termines
from tessera.services.livraison_evenements import evenements_de_livraison
from tessera.services.pipeline_events import (
    EventCallback,
    EventType,
    OrchestratorEvent,
    PipelineResult,
)
from tessera.services.build_warning import build_warnings
from tessera.services.ticket_service import TicketService
from tessera.utils.logger import get_logger

from tessera.services import pipeline_outcomes as outcomes
from tessera.services import pipeline_file as file
from tessera.services import pipeline_fin_de_file as fin_de_file
from tessera.services import pipeline_stages as stages
from tessera.services.pipeline_run import PipelineRun, set_status, tolerant
from tessera.services.pipeline_contraintes import arret_contraintes_hors_proposees
from tessera.services.pipeline_critere_protege import arret_critere_protege
from tessera.services.pipeline_approbation import apres_approbation, retenir_pour_relecture
from tessera.services.pipeline_plan import run_plan
from tessera.services.run_dans_worktree import retirer_apres_echec, retirer_en_fin_de_run
from tessera.services.pipeline_tickets import relever_etat_initial, renvoyer_si_problemes
from tessera.services.pipeline_text import (
    _compose_feedback,
    _echec_de_tests,
    _first_line,
)
from tessera.services.quota_exhaustion import is_quota_exhausted, resume_label
from tessera.services.pipeline_reprise import reprendre_sans_codeur, verifier_travail_repris
from tessera.services.session_limit import (
    extract_reset_time,
    is_session_limit,
)

if TYPE_CHECKING:
    from tessera.services.preparation_worktree import Preparation
    from tessera.services.providers.refus_garde import JournalDesRefus
    from tessera.services.carte_du_depot import CarteDuDepot
    from tessera.services.controle_visuel import ControleVisuel
    from tessera.services.quota_tracker import QuotaTracker
    from tessera.services.run_recorder import RunRecorder
    from tessera.services.run_worktree import RunWorktree
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
        worktree: "RunWorktree | None" = None,
        depot: Path | None = None,
        chemins_absents: tuple[str, ...] = (),
        preparation: "Optional[Preparation]" = None,
        etat_pr: Optional[Callable[[int], Awaitable[str]]] = None,
        journal_refus: Optional["JournalDesRefus"] = None,
        pr_mergee_de_branche: Optional[Callable[[str], Awaitable[int | None]]] = None,
        controle_visuel: "Optional[ControleVisuel]" = None,
    ) -> None:
        # Le contrôle visuel déclaré, lu avant le premier agent comme la
        # politique : un run n'obéit pas à ce que le codeur écrirait dans
        # `agents.json` (ticket-618). `None` : aucune capture, aucun serveur.
        self._controle_visuel = controle_visuel
        # Retrouve la PR mergée d'une branche `<préfixe>…` : un ticket bloqué
        # livré à la main passe en `done` au départ du run (ticket-482).
        self._pr_mergee_de_branche = pr_mergee_de_branche
        # Les écritures que le garde-fou refuse pendant un tour : le pipeline
        # les passe au reviewer et au validateur (ticket-476).
        self._journal_refus = journal_refus
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
        # Dépense du ticket en cours depuis son premier tour : remise à zéro
        # à l'entrée de chaque _run_pipeline. Permet au contrôle entre deux
        # tours de raisonner sur le ticket seul, pas sur la file (ticket-386).
        self._ticket_spent_usd = 0.0
        # True quand run_queue est en cours : oriente l'issue du contrôle de
        # budget entre deux tours (todo vs blocked, ticket-386).
        self._in_queue = False
        # Raison de la dernière interruption de file, sans le préfixe du
        # projet. L'exécuteur la lit pour que le run parent la garde (ticket-456).
        self._interruption: str | None = None
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
        # Le worktree du run (ADR-056) et le checkout dont il dépend : le
        # worktree se supprime depuis le checkout, jamais depuis lui-même.
        self._worktree = worktree
        self._depot = depot
        self._chemins_absents = chemins_absents
        # La préparation déclarée du worktree, lancée avant le codeur (ticket-536).
        self._preparation = preparation
        self._worktree_retire = False
        # Relit l'état d'une PR (« merged », « open »…). Donné à `attendre_merge`
        # pour qu'un ticket que le watcher n'a pas inscrit ne passe pas pour
        # mergé : sans lecteur, il ne l'est pas (ADR-039).
        self._etat_pr = etat_pr

    @property
    def quota(self) -> Optional["QuotaTracker"]:
        return self._quota_tracker

    @property
    def spent_usd(self) -> float:
        """Cumulative spend since this orchestrator was built."""
        return round(self._spent_usd, 10)

    @property
    def spent_ticket_usd(self) -> float:
        """Spend by the current ticket only, since its first round."""
        return round(self._ticket_spent_usd, 10)

    def record_spend(self, cost_usd: float) -> None:
        """Add one agent call's cost to the run's running total."""
        self._spent_usd += cost_usd or 0.0
        self._ticket_spent_usd += cost_usd or 0.0

    def budget_exhausted(self) -> bool:
        """True once the run has spent its ceiling. `0` means no ceiling."""
        if self._run_max_budget_usd <= 0:
            return False
        return self._spent_usd >= self._run_max_budget_usd

    def ticket_budget_exhausted(self) -> bool:
        """True once the current ticket has spent its per-ticket ceiling.

        Distinct from `budget_exhausted`: compares only the spend accumulated
        since this ticket's first round, not the cumulative queue total.  This
        prevents a long previous ticket from cutting the current one short
        (ticket-386).
        """
        if self._run_max_budget_usd <= 0:
            return False
        return self._ticket_spent_usd >= self._run_max_budget_usd

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
        """Run the ticket, then remove its worktree, if the project declared one.

        Le worktree se supprime après le commit final et la phase 1 de
        livraison ; sur toute exception, le même retrait s'applique (ADR-056).
        """
        try:
            resultat = await self._mener_le_run(
                project_id, ticket_id, on_event, run_id, dialogue, envelope_run_id
            )
            return await retirer_en_fin_de_run(self, resultat)
        finally:
            if self._worktree is not None and self._depot is not None and not self._worktree_retire:
                self._worktree_retire = True
                await retirer_apres_echec(self._worktree, self._depot)

    async def _mener_le_run(
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
        # Signalé ici, pour un run approuvé comme bloqué, avant que le ticket
        # suivant ne refasse l'état de référence des fichiers non suivis
        # (`create_branch`) et ne les range parmi les fichiers déjà présents.
        await fin_de_file.signaler_fichiers_non_suivis(self, ticket_id)
        if not resultat.approved:
            return resultat

        resultat = await apres_approbation(self, resultat, project_id, on_event)

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
        with evenements_de_livraison(on_event, ticket_id):
            livraison = retenir_pour_relecture(await self._livrer(resultat), resultat.relecture)
        for etape, duree_ms in zip(livraison.etapes, livraison.durees_ms):
            self._log(f"[{ticket_id}] livraison: {etape} ({duree_ms:.0f}ms)")
        if livraison.arret:
            self._log(f"[{ticket_id}] livraison: arrêt — {livraison.arret[:100]}")
        if livraison.branche_modifiee:
            resultat = await self._bloquer_branche_modifiee(
                resultat, livraison, project_id, on_event
            )
        # Commit the delivery log lines just written, then return to the base
        # branch so the working tree is clean after a delivered run (ticket-378).
        await fin_de_file.finaliser_livraison(self, livraison)
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
        # Une PR dont la phase 1 a levé après l'ouverture (`pr_orpheline`) est
        # surveillée malgré son `arret` ; un conflit résolu ne l'est jamais.
        if (
            livraison.pr_number is not None
            and (livraison.arret is None or livraison.pr_orpheline)
            and self._surveiller is not None
        ):
            await self._surveiller(project_id, ticket_id, livraison.pr_number, on_event)

        return resultat.model_copy(update={"livraison": livraison})

    async def _bloquer_branche_modifiee(
        self,
        resultat: PipelineResult,
        livraison: Livraison,
        project_id: str,
        on_event: EventCallback,
    ) -> PipelineResult:
        """Block the ticket when the branch moved since the approval (ticket-492).

        Rien n'a été poussé. Comme pour une CI rouge (ticket-392), la fiche du
        ticket n'est pas touchée : le tableau lit l'événement, le journal garde
        la trace. Le run se relit par un nouveau run, ou à la main.
        """
        await on_event(
            OrchestratorEvent(
                type=EventType.TICKET_STATUS_CHANGED,
                ticket_id=resultat.ticket_id,
                project_id=project_id,
                data={"status": TicketStatus.blocked.value},
            )
        )
        return resultat.model_copy(
            update={"final_status": TicketStatus.blocked, "arret": livraison.arret}
        )

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

        # Réinitialise le compteur de dépense du ticket : en file, les tickets
        # précédents ont déjà alimenté _spent_usd, et le contrôle entre deux
        # tours ne doit comparer que la dépense propre à ce ticket (ticket-386).
        self._ticket_spent_usd = 0.0

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
        await relever_etat_initial(self, run)
        await set_status(self, run, TicketStatus.in_progress)
        # Un critère qui exige un fichier que le pipeline refuse aux agents ne
        # sera jamais satisfait : inutile de payer trois tours pour l'apprendre
        # (ticket-476).
        refused = await arret_critere_protege(self, run)
        if refused is not None:
            return refused
        run.carte_du_depot = await self._carte()
        self._avertir_du_build(ticket_id)
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
            msg = str(exc)
            if is_session_limit(msg):
                reset_time = extract_reset_time(msg)
                return await outcomes.finish_session_limit(self, run, exc, reset_time)
            # Quota épuisé pendant l'appel (ticket-498) : le CLI ne laisse
            # sinon qu'un ProcessError à stderr vide.
            tracker = self._quota_tracker
            snapshot = tracker.snapshot if tracker is not None else None
            if is_quota_exhausted(exc, snapshot):
                return await outcomes.finish_quota_exhausted(
                    self, run, exc, resume_label(snapshot)
                )
            return await outcomes.finish_interrupted(self, run, exc)

    def _avertir_du_build(self, ticket_id: str) -> None:
        """Journalise un test_command qui ne lance pas le build (ticket-454).

        Ne lève jamais et ne bloque rien : un avertissement manqué laisse le
        run tel qu'avant le ticket.
        """
        if self._project_path is None:
            return
        try:
            avertissements = build_warnings(self._project_path, self._test_command)
        except Exception as exc:  # noqa: BLE001 — une aide ne doit pas coûter le run
            _logger.warning("build_warning_failed", extra={"error": str(exc)})
            return
        for message in avertissements:
            self._log(f"[{ticket_id}] {message}")

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
            # Le plafond se vérifie sur la dépense du ticket en cours depuis
            # son premier tour, et non sur le cumul de la file : un ticket
            # précédent coûteux ne doit pas couper le suivant (ticket-386).
            # Un tour 1 démarre toujours — refuser un ticket est le rôle de
            # la vérification entre tickets, pas de celle-ci (ticket-191).
            if round_num > 1 and self.ticket_budget_exhausted():
                if self._in_queue:
                    return await outcomes.finish_budget_exhausted_in_queue(self, run)
                return await outcomes.finish_budget_exhausted(self, run)

            run.start_round(round_num)
            # Sur une branche reprise, les tests passent avant le codeur : un
            # travail déjà vert va droit à l'audit (ticket-497). Le contrôle
            # précède `build_context`, pour que des tests rouges arrivent dans
            # le prompt du codeur.
            reprise_verte = round_num == 1 and await verifier_travail_repris(self, run)
            context = stages.build_context(self, run)

            # L'arrêt est vérifié **entre** les étapes, jamais au milieu de
            # l'une : couper un agent en plein tour jetterait un travail déjà
            # payé, et laisserait le diff dans un état que personne n'a relu.
            if run.stop_requested:
                return await outcomes.finish_stopped(self, run)

            produit = await self._produire_et_tester(run, context, reprise_verte)
            if isinstance(produit, PipelineResult):
                return produit
            if not produit:
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

            feedback = _compose_feedback(
                rev_approved, rev_reason, raw_verdict, val_approved, val_reason
            )
            run.review_feedback.append(feedback)
            # Le journal montre la première raison, pas le mot du verdict
            # (ticket-474) ; le codeur, lui, reçoit l'objection entière.
            self._log(
                f"[{ticket_id}] CHANGES_REQUESTED tour {round_num}: "
                f"{_first_line(feedback)[:200]}"
            )

        return await outcomes.finish_rounds_exhausted(self, run)

    async def _produire_et_tester(
        self, run: PipelineRun, context: str, reprise_verte: bool
    ) -> "PipelineResult | bool":
        """Le tour de codeur puis les tests ; ``reprise_verte`` saute les deux.

        Rend un ``PipelineResult`` quand le run se termine ici, ``False`` quand
        les tests sont rouges (le tour suivant reprend), ``True`` pour passer
        à l'audit.
        """
        if reprise_verte:
            await reprendre_sans_codeur(self, run)
            if run.stop_requested:
                return await outcomes.finish_stopped(self, run)
            return True

        await stages.run_coder(self, run, context)

        if run.stop_requested:
            return await outcomes.finish_stopped(self, run)

        # Une règle écrite hors `## Proposées` changerait la consigne de tous
        # les agents suivants sans relecture : le run s'arrête là (ticket-493).
        refused = await arret_contraintes_hors_proposees(self, run)
        if refused is not None:
            return refused

        # Une fiche de ticket en défaut (identifiant en double…) renvoie le
        # tour au producteur avant les tests (ticket-526).
        if await renvoyer_si_problemes(self, run):
            return False

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
            self._log(f"[{run.ticket_id}] tests rouges au tour {run.round_num}")
        return tests_result

    async def pick_next_ticket(self, project_id: str) -> Optional[Ticket]:
        todos = await self._ticket_svc.list_tickets(status=TicketStatus.todo)
        done_ids = await ids_termines(self._ticket_svc, todos)
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
        self, project_id: str, ticket_ids: list[str],
        on_event: EventCallback | None = None,
        dialogue: "DialogueChannel | None" = None,
        envelope_run_id: str | None = None,
        budget_override_usd: float | None = None,
    ) -> list[PipelineResult]:
        return await file.run_queue(self, project_id, ticket_ids, on_event,
                                    dialogue, envelope_run_id, budget_override_usd)

    async def run_autonomous(
        self, project_id: str, max_tickets: int = 5,
        on_event: EventCallback | None = None,
        envelope_run_id: str | None = None,
    ) -> list[PipelineResult]:
        return await file.run_autonomous(
            self, project_id, max_tickets, on_event, envelope_run_id)

    @property
    def interruption(self) -> str | None:
        """Why the last queue stopped early (``file interrompue : …``), if it did."""
        return self._interruption

    def _interrompre(self, project_id: str, raison: str) -> None:
        """Log the queue interruption and keep its reason for the parent run."""
        self._interruption = f"file interrompue : {raison}"
        self._log(f"[{project_id}] {self._interruption}")

    def _log(self, message: str) -> None:
        ajouter_ligne(self._log_path, message)


__all__ = [
    "EventCallback",
    "EventType",
    "Orchestrator",
    "OrchestratorEvent",
    "PipelineResult",
]
