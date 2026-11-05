"""Redeliver, once, the approved tickets whose delivery stopped — ticket-792.

A delivery exception does not fail the run (ADR-030): the work stays on a local
branch. The queue reports such a ticket as `non_livres` and, once its last
ticket has passed, runs the delivery again — the same path, never a forced
push (ADR-022). A second failure leaves the ticket where it is.
"""
from typing import TYPE_CHECKING

from tessera.models.ticket import TicketStatus
from tessera.services.pipeline_events import (
    EventCallback,
    EventType,
    OrchestratorEvent,
    PipelineResult,
)
from tessera.services.pipeline_livraison import livrer_le_resultat
from tessera.utils.logger import get_logger

if TYPE_CHECKING:
    from tessera.services.orchestrator import Orchestrator

_logger = get_logger(__name__)


def est_non_livre(result: PipelineResult) -> bool:
    """True for an approved ticket whose delivery stopped and opened no PR."""
    livraison = result.livraison
    return (
        result.approved
        and result.final_status == TicketStatus.blocked
        and livraison is not None
        and livraison.pr_number is None
        and bool(livraison.arret)
    )


async def _relivrer(
    orch: "Orchestrator", project_id: str, result: PipelineResult, callback: EventCallback
) -> PipelineResult:
    """Run the delivery of one undelivered ticket again, from its local branch."""
    if orch._git_workspace is not None and result.branch is not None:
        await orch._git_workspace.se_placer_sur(result.branch)
    # Le premier échec a bloqué le résultat : la reprise repart d'un ticket approuvé.
    neuf = result.model_copy(
        update={"final_status": TicketStatus.done, "arret": None, "livraison": None}
    )
    neuf = await livrer_le_resultat(orch, neuf, project_id, callback)
    if not est_non_livre(neuf):
        await callback(
            OrchestratorEvent(
                type=EventType.TICKET_STATUS_CHANGED,
                ticket_id=neuf.ticket_id,
                project_id=project_id,
                data={"status": neuf.final_status.value},
            )
        )
    return neuf


async def relivrer_les_non_livres(
    orch: "Orchestrator",
    project_id: str,
    results: list[PipelineResult],
    callback: EventCallback,
) -> list[str]:
    """Redeliver each undelivered ticket once; return those still undelivered.

    `results` is updated in place for the tickets delivered this time. An
    exception is logged and keeps the ticket undelivered (ADR-030).
    """
    for i, result in enumerate(results):
        if not est_non_livre(result):
            continue
        try:
            results[i] = await _relivrer(orch, project_id, result, callback)
        except Exception as exc:  # noqa: BLE001 — ADR-030 : la livraison ne fait pas échouer le run
            _logger.warning(
                "relivraison_echouee", extra={"ticket": result.ticket_id, "erreur": str(exc)}
            )
            orch._log(f"[{result.ticket_id}] relivraison: échec — {str(exc)[:100]}")
            continue
        recorder, run_id = orch._run_recorder, result.run_id
        if recorder is not None and run_id is not None:
            await recorder.clore(run_id, results[i])
    return [r.ticket_id for r in results if est_non_livre(r)]
