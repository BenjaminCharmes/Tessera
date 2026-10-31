"""Queue and autonomous run modes — ticket-685.

`Orchestrator.run_queue` and `Orchestrator.run_autonomous` delegate here, as
the stages delegate to the `pipeline_*` modules. The loop runs the checks
between two tickets in a fixed order (stop requested, spending ceiling,
ticket already finished): stopping in the middle of a ticket would leave its
work uncommitted (ADR-018, ADR-020).
"""
from typing import TYPE_CHECKING

from tessera.models.ticket import TicketStatus
from tessera.services.dialogue import DialogueChannel
from tessera.services.file_vivante import fermer_si_vivante, marquer_position_si_vivante
from tessera.services.pipeline_events import (
    EventCallback,
    EventType,
    OrchestratorEvent,
    PipelineResult,
)
from tessera.services.pipeline_file_livraison import livraison_arrete_la_file
from tessera.services.pipeline_file_tour import Tour, progres
from tessera.services.pipeline_fin_de_file import nettoyer_apres_file
from tessera.services.pipeline_run import tolerant
from tessera.services.session_limit import extract_reset_time_from_arret
from tessera.utils.logger import get_logger

if TYPE_CHECKING:
    from tessera.services.orchestrator import Orchestrator

_logger = get_logger(__name__)


async def _noop(event: OrchestratorEvent) -> None:
    pass


def plafond_effectif(
    orch: "Orchestrator", nb_tickets: int, override: float | None
) -> float:
    """Spending ceiling of the whole queue; 0 means no ceiling.

    The per-ticket ceiling times the ticket count, unless the request fixes
    its own (ticket-383). The count is the current one: tickets appended
    along the way each get their share (ticket-478).
    """
    if override is not None:
        return override
    if orch._run_max_budget_usd > 0:
        return orch._run_max_budget_usd * nb_tickets
    return 0.0


def _arret_demande(
    orch: "Orchestrator", project_id: str, dialogue: DialogueChannel | None
) -> bool:
    if dialogue is None or not dialogue.stop_requested:
        return False
    orch._interrompre(project_id, "arrêt demandé")
    return True


async def _plafond_atteint(
    orch: "Orchestrator", tour: Tour, plafond: float, callback: EventCallback
) -> bool:
    if plafond <= 0 or orch._spent_usd < plafond:
        return False
    orch._interrompre(
        tour.project_id,
        f"plafond de dépense ({orch._spent_usd:.2f} $ / {plafond:.2f} $)",
    )
    donnees = tour.donnees(depuis=tour.index - 1) | {
        "raison": "budget",
        "spent_usd": orch._spent_usd,
        "budget_usd": plafond,
    }
    await progres(callback, tour.ticket_id, donnees)
    return True


async def _arret_avant_ticket(
    orch: "Orchestrator",
    tour: Tour,
    dialogue: DialogueChannel | None,
    override: float | None,
    callback: EventCallback,
) -> bool:
    """True when the queue stops before this ticket: stop requested, or ceiling hit."""
    if _arret_demande(orch, tour.project_id, dialogue):
        return True
    plafond = plafond_effectif(orch, len(tour.ticket_ids), override)
    return await _plafond_atteint(orch, tour, plafond, callback)


async def _deja_termine(orch: "Orchestrator", tour: Tour) -> bool:
    """Skip a finished ticket rather than stop: the others still get their turn.

    Re-running it redoes delivered work on a fresh branch at the quota's
    expense; the endpoint can be called directly, so the queue guards it
    (ticket-115).
    """
    if not await orch._est_termine(tour.ticket_id):
        return False
    orch._log(f"[{tour.project_id}] {tour.ticket_id} sauté : déjà terminé")
    return True


async def _arret_non_approuve(
    orch: "Orchestrator", tour: Tour, result: PipelineResult, callback: EventCallback
) -> None:
    """Log why an unapproved ticket stops the queue, and say so on the event stream."""
    if result.final_status != TicketStatus.todo:
        orch._interrompre(tour.project_id, f"{tour.ticket_id} non approuvé")
        return
    arret = result.arret or ""
    if arret.startswith("run budget exhausted"):
        # Plafond par ticket atteint entre deux tours : le ticket a déjà loggé
        # la raison dans finish_budget_exhausted_in_queue (ticket-386).
        orch._interrompre(tour.project_id, f"{tour.ticket_id} — budget ({arret[:80]})")
        extra: dict[str, object] = {"raison": "budget"}
    elif arret.startswith("quota_exhausted"):
        # Quota d'abonnement épuisé en plein ticket : le ticket est en todo,
        # le journal a déjà dit l'heure (ticket-498).
        orch._interrompre(tour.project_id, "quota épuisé")
        extra = {"raison": "quota_exhausted"}
    else:
        # Limite de session : le ticket est remis en todo, la file s'arrête
        # proprement avant le suivant.
        reset_time = extract_reset_time_from_arret(result.arret)
        reprise = f" (reprise : {reset_time})" if reset_time else ""
        orch._interrompre(tour.project_id, f"limite de session{reprise}")
        extra = {"raison": "session_limit", "reset_time": reset_time or ""}
    await progres(callback, tour.ticket_id, tour.donnees() | extra)


async def run_queue(
    orch: "Orchestrator",
    project_id: str,
    ticket_ids: list[str],
    on_event: EventCallback | None = None,
    dialogue: DialogueChannel | None = None,
    envelope_run_id: str | None = None,
    budget_override_usd: float | None = None,
) -> list[PipelineResult]:
    """Run a selection of tickets, in the requested order.

    Unlike `run_autonomous`, which picks the next ticket itself, the user named
    a batch and its order.

    **An unapproved ticket stops the queue.** The tickets of a batch almost
    always depend on each other (that is how the planner cuts them), and
    chaining onto a base nobody validated would make the next one work on a
    doubtful state.

    The spending ceiling defaults to `run_max_budget_usd × ticket count`
    (ticket-383); ``budget_override_usd`` replaces that when the request sets
    a budget. `ticket_ids` may grow during the loop (ticket-478).
    """
    callback = tolerant(on_event or _noop)
    results: list[PipelineResult] = []
    orch._in_queue = True
    orch._interruption = None
    for index, ticket_id in enumerate(ticket_ids, start=1):
        # Dit à la file vivante où en est la boucle : un retrait ne touche que
        # ce qui est après (ticket-513).
        marquer_position_si_vivante(ticket_ids, index)
        tour = Tour(project_id, ticket_ids, index, ticket_id)
        if await _arret_avant_ticket(orch, tour, dialogue, budget_override_usd, callback):
            break
        if await _deja_termine(orch, tour):
            continue
        await progres(callback, ticket_id, tour.donnees())
        result = await orch.run_pipeline(
            project_id, ticket_id, callback, dialogue=dialogue,
            envelope_run_id=envelope_run_id,
        )
        results.append(result)
        if not result.approved:
            await _arret_non_approuve(orch, tour, result, callback)
            break
        if await livraison_arrete_la_file(orch, tour, results, callback):
            break
    # Fermer **avant** le premier `await` suivant : un ajout qui passerait
    # entre la fin de la lecture et ici rendrait 200 sans jamais s'exécuter.
    fermer_si_vivante(ticket_ids)
    orch._in_queue = False
    await nettoyer_apres_file(orch)
    return results


def _budget_epuise(orch: "Orchestrator", project_id: str) -> bool:
    """True when the spent estimate reached the run ceiling (ADR-018)."""
    if not orch.budget_exhausted():
        return False
    _logger.warning(
        "run_budget_exhausted",
        extra={"spent_usd": orch.spent_usd, "max_usd": orch._run_max_budget_usd},
    )
    orch._log(
        f"[{project_id}] run interrompu : {orch.spent_usd:.2f} USD "
        f"dépensés sur {orch._run_max_budget_usd:.2f} autorisés"
    )
    return True


async def _quota_bas(
    orch: "Orchestrator", project_id: str, callback: EventCallback
) -> bool:
    """True when the real subscription quota is low; an unknown quota never stops."""
    tracker = orch._quota_tracker
    if tracker is None or not tracker.is_low():
        return False
    snapshot = tracker.snapshot
    _logger.warning(
        "run_quota_low",
        extra={"utilization": snapshot.utilization if snapshot else None},
    )
    orch._log(
        f"[{project_id}] run interrompu : quota d'abonnement à "
        f"{(snapshot.utilization * 100) if snapshot else 0:.0f} %"
    )
    await callback(
        OrchestratorEvent(
            type=EventType.QUOTA_UPDATED,
            ticket_id="",
            data={**tracker.as_event_data(), "run_interrupted": True},
        )
    )
    return True


async def run_autonomous(
    orch: "Orchestrator",
    project_id: str,
    max_tickets: int = 5,
    on_event: EventCallback | None = None,
    envelope_run_id: str | None = None,
) -> list[PipelineResult]:
    """Pick and run the next eligible ticket, up to `max_tickets`.

    The ceiling and the quota are checked *between* tickets: interrupting one
    would leave its work uncommitted (ADR-018, ADR-020, ticket-054).
    """
    callback = tolerant(on_event or _noop)
    results: list[PipelineResult] = []
    for _ in range(max_tickets):
        if _budget_epuise(orch, project_id):
            break
        if await _quota_bas(orch, project_id, callback):
            break
        ticket = await orch.pick_next_ticket(project_id)
        if ticket is None:
            break
        results.append(
            await orch.run_pipeline(
                project_id, ticket.id, callback, envelope_run_id=envelope_run_id
            )
        )
    return results
