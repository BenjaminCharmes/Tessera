"""Wait for the merge of a PR that a remaining queue ticket depends on."""
from collections.abc import Awaitable, Callable
from typing import Any

from tessera.services.livraison import Livraison
from tessera.services.livraison_evenements import attente_annoncee
from tessera.services.pipeline_events import EventCallback
from tessera.services.ticket_service import TicketService


async def attendre_si_dependant(
    ticket_svc: TicketService,
    ci_watcher: Any,
    project_id: str,
    ticket_id: str,
    restants: list[str],
    pr_number: int | None = None,
    etat_pr: Callable[[int], Awaitable[str]] | None = None,
    on_event: EventCallback | None = None,
) -> bool | None:
    """Await the CI merge for ``ticket_id`` if a remaining ticket depends on it.

    Walks ``restants`` to find the first ticket that declares ``ticket_id``
    in its ``depends_on``. When found, suspends until ``CIWatcher`` signals
    that ``ticket_id`` is no longer in the waiting set (merged or blocked).
    ``pr_number`` and ``etat_pr`` let the watcher re-read a PR it never
    registered, instead of assuming it merged.

    Returns None when no remaining ticket depends on it (nothing awaited),
    True when it merged (the caller realigns the base, ticket-403), and False
    when it did not (the queue must stop).
    """
    for tid_dep in restants:
        ticket_dep = await ticket_svc.get_ticket(tid_dep)
        if ticket_dep is not None and ticket_id in ticket_dep.depends_on:
            async with attente_annoncee(on_event, ticket_id, pr_number):
                merge = await ci_watcher.attendre_merge(
                    project_id, ticket_id, pr_number=pr_number, etat_pr=etat_pr
                )
            return bool(merge)
    return None


async def dependants_a_sauter(
    ticket_svc: TicketService,
    ticket_id: str,
    restants: list[str],
) -> dict[str, str]:
    """Find the remaining tickets that depend, directly or not, on ``ticket_id``.

    Returns ``{skipped id: dependency that makes it skip}``: ``ticket_id`` for
    a direct dependent, the skipped intermediate ticket for a transitive one.
    Unknown tickets are ignored. Order of ``restants`` does not matter.
    """
    depends: dict[str, list[str]] = {}
    for tid in restants:
        ticket = await ticket_svc.get_ticket(tid)
        if ticket is not None:
            depends[tid] = list(ticket.depends_on)
    sautes: dict[str, str] = {}
    trouve = True
    while trouve:
        trouve = False
        for tid, deps in depends.items():
            if tid in sautes:
                continue
            cause = next((d for d in deps if d == ticket_id or d in sautes), None)
            if cause is not None:
                sautes[tid] = cause
                trouve = True
    return sautes


async def sauter_dependants(
    ticket_svc: TicketService,
    project_id: str,
    ticket_id: str,
    ticket_ids: list[str],
    index: int,
    journal: Callable[[str], None],
) -> bool:
    """Drop from the queue the tickets that depend on an unmerged ``ticket_id``.

    Direct and transitive dependents (ticket-569, ADR-060) are removed in place,
    only after position ``index`` (1-based, so ``ticket_ids[index:]`` is what
    remains), each logged with the dependency that makes it skip. Returns True
    when tickets remain in the queue, False when the queue is empty.
    """
    sautes = await dependants_a_sauter(ticket_svc, ticket_id, ticket_ids[index:])
    for saute, dependance in sautes.items():
        del ticket_ids[ticket_ids.index(saute, index)]
        suite = "non mergé" if dependance == ticket_id else "sauté"
        journal(f"[{project_id}] {saute} sauté : dépend de {dependance}, {suite}")
    return bool(ticket_ids[index:])


def journal_confiee(project_id: str, ticket_id: str, livraison: Livraison) -> str:
    """Log line saying whether the PR of ``ticket_id`` is watched by CIWatcher.

    `surveiller` is only called for a PR without a stop (or an orphan one):
    otherwise nobody watches it.
    """
    surveillee = livraison.arret is None or livraison.pr_orpheline
    etat = "confiée au CIWatcher" if surveillee else "non surveillée (livraison arrêtée)"
    return f"[{project_id}] {ticket_id} PR #{livraison.pr_number} {etat}"
