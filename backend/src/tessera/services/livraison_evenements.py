"""Events of the delivery and queue waits that used to be silent — ticket-559.

Two silences: the queue suspending on a PR another ticket depends on, and the
conflict resolver working during the rebase. Nothing here decides anything; it
only announces, and an announcement that fails never breaks the run.
"""
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager

from tessera.services.livraison_conflit import poser_signal
from tessera.services.pipeline_events import EventCallback, EventType, OrchestratorEvent
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)


async def _publier(on_event: EventCallback, event: OrchestratorEvent) -> None:
    try:
        await on_event(event)
    except Exception as exc:  # noqa: BLE001 — annoncer ne doit rien casser
        _logger.warning("evenement_non_publie", extra={"type": event.type.value, "erreur": str(exc)})


@contextmanager
def evenements_de_livraison(on_event: EventCallback, ticket_id: str) -> Iterator[None]:
    """Announce the conflict resolution of the delivery launched inside the block."""

    async def signaler(phase: str, fichiers: tuple[str, ...], issue: str | None) -> None:
        data: dict[str, object] = {"phase": phase, "files": list(fichiers), "outcome": issue}
        await _publier(
            on_event,
            OrchestratorEvent(type=EventType.CONFLICT_RESOLUTION, ticket_id=ticket_id, data=data),
        )

    with poser_signal(signaler):
        yield


@asynccontextmanager
async def attente_annoncee(
    on_event: EventCallback | None, ticket_id: str, pr_number: int | None
) -> AsyncIterator[None]:
    """Announce ``waiting: true`` now and ``waiting: false`` however the block ends.

    Without a listener (``on_event`` is None) the wait stays silent.
    """
    if on_event is None:
        yield
        return

    async def annoncer(waiting: bool) -> None:
        data: dict[str, object] = {
            "reason": "dependency",
            "waiting": waiting,
            "ticket": ticket_id,
            "pr_number": pr_number,
        }
        await _publier(
            on_event,
            OrchestratorEvent(type=EventType.EXTERNAL_WAIT, ticket_id=ticket_id, data=data),
        )

    await annoncer(True)
    try:
        yield
    finally:
        await annoncer(False)
