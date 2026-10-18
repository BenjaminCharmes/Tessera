"""Put away the blocked tickets that were delivered by hand — ticket-482.

A ticket the pipeline blocked, then checked and merged by hand, stays in
`tickets/blocked/` on the base: nothing tells the project it is over. At the
start of a run, each blocked ticket whose branch has a merged PR goes to
`done/` with that PR's number. The move happens before the bookkeeping commit,
so it leaves with the run's own branch like every other change to `tickets/`.
"""
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from tessera.models.ticket import TicketStatus
from tessera.utils.logger import get_logger

if TYPE_CHECKING:
    from tessera.services.orchestrator import Orchestrator

_logger = get_logger(__name__)


async def ranger_les_bloques_livres(
    orch: "Orchestrator", ticket_en_cours: str
) -> list[str]:
    """Move to `done` every blocked ticket whose branch was merged; return log lines.

    The lines are returned, not logged: written now, they would land in a commit
    on the base. A GitHub error leaves the ticket blocked and never stops the
    run — nothing here is a safety gate.
    """
    # getattr : les doubles d'orchestrateur des tests d'étape n'ont pas de chercheur.
    chercher = getattr(orch, "_pr_mergee_de_branche", None)
    if chercher is None:
        return []
    try:
        bloques = await orch._ticket_svc.list_tickets(TicketStatus.blocked)
    except Exception as exc:
        _logger.warning("blocked_tickets_listing_failed", extra={"error": str(exc)})
        return []

    lignes: list[str] = []
    for ticket in bloques:
        if ticket.id == ticket_en_cours:
            continue
        ligne = await _ranger_si_livre(orch, ticket.id, chercher)
        if ligne is not None:
            lignes.append(ligne)
    return lignes


async def _ranger_si_livre(
    orch: "Orchestrator",
    ticket_id: str,
    chercher: Callable[[str], Awaitable[int | None]],
) -> str | None:
    """Move one ticket to `done` when its branch has a merged PR; else None."""
    try:
        # Le tiret final : `ticket-48-` ne doit pas attraper `ticket-482-…`.
        pr_number = await chercher(f"{ticket_id}-")
        if pr_number is None:
            return None
        await orch._ticket_svc.update_status(ticket_id, TicketStatus.done)
        await orch._ticket_svc.set_pr_number(ticket_id, pr_number)
    except Exception as exc:
        _logger.warning(
            "blocked_ticket_putaway_failed",
            extra={"ticket_id": ticket_id, "error": str(exc)},
        )
        return None
    return f"{ticket_id} rangé en done : PR #{pr_number} mergée"
