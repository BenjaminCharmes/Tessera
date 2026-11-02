"""What a ticket's delivery does to the queue — ticket-685.

After an approved ticket, the queue waits for its merge, skips its dependents
or stops, depending on what the delivery produced (ADR-051, ADR-060).
"""
from typing import TYPE_CHECKING

from tessera.services.attente_dependance import (
    attendre_si_dependant,
    journal_confiee,
    sauter_dependants,
)
from tessera.services.livraison import Livraison
from tessera.services.pipeline_events import EventCallback, PipelineResult
from tessera.services.pipeline_file_tour import Tour
from tessera.services.pipeline_fin_de_file import (
    attendre_merge_et_syncer,
    realigner_base,
)
from tessera.services.ticket_service import TicketService

if TYPE_CHECKING:
    from tessera.services.orchestrator import Orchestrator


async def _trouver_bloquant(
    ticket_svc: TicketService,
    ticket_id: str,
    pr_number: int,
    restants: list[str],
) -> Livraison | None:
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
    livraison: Livraison | None,
    restants: list[str],
) -> Livraison | None:
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


async def _sans_dependants_sautes(orch: "Orchestrator", tour: Tour) -> bool:
    """True when the unmerged ticket has no dependent to skip, so the queue stops."""
    if await sauter_dependants(
        orch._ticket_svc, tour.project_id, tour.ticket_id,
        tour.ticket_ids, tour.index, orch._log,
    ):
        return False
    orch._interrompre(tour.project_id, f"{tour.ticket_id} non mergé")
    return True


async def _attente_merge_sans_ci(
    orch: "Orchestrator", tour: Tour, pr_number: int, callback: EventCallback
) -> bool:
    """merge_without_ci: wait for every next ticket, dependent or not (ticket-382).

    Returns True when the queue stops.
    """
    merge = await attendre_merge_et_syncer(
        orch, tour.project_id, tour.ticket_id, pr_number, callback
    )
    return not merge and await _sans_dependants_sautes(orch, tour)


async def _attente_merge_des_dependants(
    orch: "Orchestrator",
    tour: Tour,
    livraison: Livraison,
    pr_number: int,
    callback: EventCallback,
) -> bool:
    """CIWatcher (ADR-051): dependents wait for the merge, the others start.

    Returns True when the queue stops.
    """
    merge = await attendre_si_dependant(
        orch._ticket_svc,
        orch._ci_watcher,
        tour.project_id,
        tour.ticket_id,
        tour.restants,
        pr_number=pr_number,
        etat_pr=orch._etat_pr,
        on_event=callback,
    )
    if merge is False and await _sans_dependants_sautes(orch, tour):
        return True
    if merge:
        # Le ticket suivant en dépend : il doit partir de la base qui contient
        # ce merge, pas de la base locale d'avant (ticket-403).
        await realigner_base(orch, tour.project_id, tour.ticket_id)
    orch._log(journal_confiee(tour.project_id, tour.ticket_id, livraison))
    return False


async def _pr_ouverte(
    orch: "Orchestrator",
    tour: Tour,
    livraison: Livraison,
    pr_number: int,
    results: list[PipelineResult],
    callback: EventCallback,
) -> bool:
    """A PR is open: True when the queue stops."""
    if orch._ci_watcher is None:
        # Sans CIWatcher : on s'arrête si le ticket suivant dépend de celui-ci.
        bloquant = await _trouver_bloquant(
            orch._ticket_svc, tour.ticket_id, pr_number, tour.restants
        )
        if bloquant is None:
            return False
        results[-1] = results[-1].model_copy(update={"livraison": bloquant})
        return True
    if orch._merge_without_ci and tour.restants:
        return await _attente_merge_sans_ci(orch, tour, pr_number, callback)
    return await _attente_merge_des_dependants(orch, tour, livraison, pr_number, callback)


async def _sans_pr(
    orch: "Orchestrator",
    tour: Tour,
    livraison: Livraison | None,
    results: list[PipelineResult],
) -> bool:
    """Approved but no PR: a dependent would start from a base without it (ticket-361).

    The queue stops rather than let that ticket produce work to throw away.
    """
    bloquant = await _trouver_bloquant_sans_pr(
        orch._ticket_svc, tour.ticket_id, livraison, tour.restants
    )
    if bloquant is None:
        return False
    results[-1] = results[-1].model_copy(update={"livraison": bloquant})
    orch._interrompre(tour.project_id, f"{tour.ticket_id} n'a pas été livré")
    return True


async def livraison_arrete_la_file(
    orch: "Orchestrator",
    tour: Tour,
    results: list[PipelineResult],
    callback: EventCallback,
) -> bool:
    """True when the delivery of the ticket just run stops the queue."""
    livraison = results[-1].livraison
    if livraison is not None and livraison.pr_number is not None:
        return await _pr_ouverte(
            orch, tour, livraison, livraison.pr_number, results, callback
        )
    return await _sans_pr(orch, tour, livraison, results)
