"""Position of the queue loop and its progress event — ticket-685."""
from dataclasses import dataclass

from tessera.services.pipeline_events import EventCallback, EventType, OrchestratorEvent


@dataclass(frozen=True)
class Tour:
    """Where the queue loop stands: the project, the live list and the position."""

    project_id: str
    ticket_ids: list[str]
    index: int
    ticket_id: str

    @property
    def restants(self) -> list[str]:
        return self.ticket_ids[self.index :]

    def donnees(self, depuis: int | None = None) -> dict[str, object]:
        """The `QUEUE_PROGRESS` payload; `depuis` moves the start of `restants`."""
        debut = self.index if depuis is None else depuis
        return {
            "index": self.index,
            "total": len(self.ticket_ids),
            "restants": list(self.ticket_ids[debut:]),
            "faits": list(self.ticket_ids[: self.index - 1]),
        }


async def progres(
    callback: EventCallback, ticket_id: str, data: dict[str, object]
) -> None:
    """Emit one `QUEUE_PROGRESS` event."""
    await callback(
        OrchestratorEvent(type=EventType.QUEUE_PROGRESS, ticket_id=ticket_id, data=data)
    )
