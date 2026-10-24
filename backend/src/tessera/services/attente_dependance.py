"""Wait for the merge of a PR that a remaining queue ticket depends on."""
from collections.abc import Awaitable, Callable
from typing import Any

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
