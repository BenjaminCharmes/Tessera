"""State shared by the stages of one pipeline run — ticket-046.

`run_pipeline` used to carry this as local variables threaded through 490
inline lines. Naming it makes explicit what each stage may read and what it
hands to the next, and gives the per-round reset a single place to live.
"""
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from vibe_ide.models.ticket import Ticket, TicketStatus
from vibe_ide.services.dialogue import DialogueChannel
from vibe_ide.services.pipeline_events import (
    EventCallback,
    EventType,
    OrchestratorEvent,
)

if TYPE_CHECKING:
    from vibe_ide.services.orchestrator import Orchestrator


@dataclass
class PipelineRun:
    """Everything a stage needs to read, or to hand to the next one.

    The per-round fields are cleared by `start_round`: they describe the
    current attempt, not the run as a whole. Forgetting that reset is how a
    second round would review the first round's diff.
    """

    project_id: str
    ticket: Ticket
    on_event: EventCallback
    run_id: str | None = None

    branch: str | None = None
    review_feedback: list[str] = field(default_factory=list)

    # Le dialogue avec l'utilisateur pendant le run (ticket-066). Par défaut
    # non interactif : un run lancé sans canal branché — un test, un appel
    # programmatique — ne doit jamais se suspendre en attendant une réponse
    # que personne ne viendra donner.
    dialogue: DialogueChannel = field(
        default_factory=lambda: DialogueChannel(interactive=False)
    )

    # --- remis à zéro à chaque tour ---
    round_num: int = 0
    reviewed_code: str = ""
    test_result: Any = None
    test_context: str = ""
    security_context: str = ""

    @property
    def stop_requested(self) -> bool:
        """True dès que l'utilisateur a demandé l'arrêt de ce run."""
        return self.dialogue.stop_requested

    @property
    def ticket_id(self) -> str:
        return self.ticket.id

    def start_round(self, round_num: int) -> None:
        self.round_num = round_num
        self.reviewed_code = ""
        self.test_result = None
        self.test_context = ""
        self.security_context = ""


async def emit(run: PipelineRun, event_type: EventType, **data: Any) -> None:
    """Emit a ticket-scoped event with `data` built from keyword arguments."""
    await run.on_event(
        OrchestratorEvent(type=event_type, ticket_id=run.ticket_id, data=dict(data))
    )


async def set_status(
    orch: "Orchestrator", run: PipelineRun, status: TicketStatus
) -> None:
    """Move the ticket to `status` and announce it — always both.

    The folder carries the status and the UI listens to the event: updating
    one without the other makes the board disagree with the filesystem.
    """
    await orch._ticket_svc.update_status(run.ticket_id, status)
    await emit(run, EventType.TICKET_STATUS_CHANGED, status=status.value)
