"""Read a ticket that only exists on the remote base — ticket-923.

Un projet sans worktree travaille dans son checkout : un ticket mergé sur
`origin/<base>` n'y est qu'après l'avance rapide que `create_branch` fait,
mais celle-ci vient après la lecture du ticket. Ce module la fait plus tôt,
une seule fois, quand le ticket manque à l'arbre.
"""
from typing import TYPE_CHECKING

from tessera.models.ticket import Ticket, TicketStatus
from tessera.services.git_workspace import journal_attente, journal_en_attente
from tessera.services.noyau.pipeline_events import PipelineResult
from tessera.services.pipeline import pipeline_branche
from tessera.utils.logger import get_logger

if TYPE_CHECKING:
    from tessera.services.pipeline.orchestrator import Orchestrator

_logger = get_logger(__name__)


async def _avancer(orch: "Orchestrator") -> str | None:
    """Fast-forward the base with the pending log lines set aside, then put them back."""
    racine = orch._project_path
    lignes = await journal_en_attente.mettre_de_cote(racine) if racine else []
    if racine:
        lignes += await journal_attente.reprendre(racine)
    try:
        return await pipeline_branche._realigner_base_au_depart(orch)
    finally:
        pipeline_branche._reecrire_journal(racine, lignes)


async def lire_apres_avance(
    orch: "Orchestrator", ticket_id: str
) -> tuple[Ticket | None, str | None] | None:
    """The ticket read after realigning the base, and the refusal reason if any.

    Sans workspace git, ou dans un worktree de run (qui part déjà de
    `origin/<base>`), rien n'est tenté : `None`.
    """
    if orch._git_workspace is None or getattr(orch, "_worktree", None) is not None:
        return None
    raison = await _avancer(orch)
    ticket = await orch._ticket_svc.get_ticket(ticket_id)
    if ticket is None:
        _logger.info("ticket_absent_apres_avance", extra={"ticket_id": ticket_id, "raison": raison})
    return ticket, raison


def arret_ticket_absent(ticket_id: str, raison: str | None) -> PipelineResult:
    """A blocked result, with nothing created, saying why the ticket is still missing."""
    cause = f" (avance de la base refusée : {raison})" if raison else ""
    return PipelineResult(
        ticket_id=ticket_id,
        final_status=TicketStatus.blocked,
        rounds=0,
        approved=False,
        arret=f"Ticket introuvable : {ticket_id}{cause}",
    )


async def trouver_ticket(orch: "Orchestrator", ticket_id: str) -> Ticket | PipelineResult:
    """The ticket of a run: tree, then restored from the base, then after the fast-forward.

    Absent partout : `ValueError` hors avance tentée, sinon un résultat bloqué.
    Le fichier ticket a pu être déplacé sans commit lors d'un run précédent coupé
    net (ex : blocked/ sans commit) : on le retrouve sur la base distante.
    """
    ticket = await orch._ticket_svc.get_ticket(ticket_id)
    if ticket is None and orch._git_workspace is not None:
        if await orch._git_workspace.restaurer_ticket_depuis_base(ticket_id):
            ticket = await orch._ticket_svc.get_ticket(ticket_id)
    if ticket is not None:
        return ticket
    avance = await lire_apres_avance(orch, ticket_id)
    if avance is None:
        raise ValueError(f"Ticket introuvable : {ticket_id}")
    return avance[0] if avance[0] is not None else arret_ticket_absent(ticket_id, avance[1])
