from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from vibe_ide.models.agent import AgentConfig, AgentRole
from vibe_ide.models.ticket import Ticket, TicketPriority, TicketStatus
from vibe_ide.services.agent_runner import AgentRunner
from vibe_ide.services.ticket_service import TicketService
from vibe_ide.utils.logger import get_logger

_logger = get_logger(__name__)

_PRIORITY_ORDER: dict[TicketPriority, int] = {
    TicketPriority.critical: 0,
    TicketPriority.high: 1,
    TicketPriority.medium: 2,
    TicketPriority.low: 3,
}


class EventType(str, Enum):
    AGENT_STARTED = "agent_started"
    AGENT_TOKEN = "agent_token"
    AGENT_DONE = "agent_done"
    TICKET_STATUS_CHANGED = "ticket_status_changed"
    PIPELINE_DONE = "pipeline_done"
    ERROR = "error"


class OrchestratorEvent(BaseModel):
    type: EventType
    agent: Optional[AgentRole] = None
    ticket_id: str
    data: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PipelineResult(BaseModel):
    ticket_id: str
    final_status: TicketStatus
    rounds: int
    approved: bool


EventCallback = Callable[[OrchestratorEvent], Awaitable[None]]


def _parse_reviewer_verdict(content: str) -> tuple[bool, str]:
    """Returns (approved, reason). CHANGES_REQUESTED takes priority over APPROVED."""
    for line in content.splitlines():
        if "CHANGES_REQUESTED" in line.upper():
            reason = line.split(":", 1)[-1].strip() if ":" in line else ""
            return False, reason
    if "APPROVED" in content.upper():
        return True, ""
    return False, content[:200]


class Orchestrator:
    def __init__(
        self,
        runner: AgentRunner,
        ticket_service: TicketService,
        project_context: str,
        agent_configs: list[AgentConfig],
        pipeline_log_path: Path,
        max_review_rounds: int = 3,
    ) -> None:
        self._runner = runner
        self._ticket_svc = ticket_service
        self._project_context = project_context
        self._agent_configs = agent_configs
        self._log_path = pipeline_log_path
        self._max_review_rounds = max_review_rounds

    async def run_pipeline(
        self,
        project_id: str,
        ticket_id: str,
        on_event: EventCallback,
    ) -> PipelineResult:
        ticket = await self._ticket_svc.get_ticket(ticket_id)
        if ticket is None:
            raise ValueError(f"Ticket introuvable : {ticket_id}")

        codeur_cfg = next(
            (c for c in self._agent_configs if c.role == AgentRole.codeur.value), None
        )
        reviewer_cfg = next(
            (c for c in self._agent_configs if c.role == AgentRole.reviewer.value), None
        )

        await self._ticket_svc.update_status(ticket_id, TicketStatus.in_progress)
        await on_event(
            OrchestratorEvent(
                type=EventType.TICKET_STATUS_CHANGED,
                ticket_id=ticket_id,
                data={"status": TicketStatus.in_progress.value},
            )
        )

        review_feedback: list[str] = []

        for round_num in range(1, self._max_review_rounds + 1):
            context = self._project_context
            if review_feedback:
                feedback_block = "\n\n## Retours reviewer précédents\n" + "\n---\n".join(
                    f"Tour {i + 1}: {fb}" for i, fb in enumerate(review_feedback)
                )
                context = self._project_context + feedback_block

            # --- codeur ---
            await on_event(
                OrchestratorEvent(
                    type=EventType.AGENT_STARTED,
                    agent=AgentRole.codeur,
                    ticket_id=ticket_id,
                    data={"round": round_num},
                )
            )
            self._log(f"[{ticket_id}] tour {round_num} — codeur démarré")

            async def _emit_token(token: str, tid: str = ticket_id) -> None:
                await on_event(
                    OrchestratorEvent(
                        type=EventType.AGENT_TOKEN,
                        agent=AgentRole.codeur,
                        ticket_id=tid,
                        data={"token": token},
                    )
                )

            codeur_result = await self._runner.run(
                role=AgentRole.codeur,
                ticket=ticket,
                project_context=context,
                agent_config=codeur_cfg,
                stream_callback=_emit_token,
            )
            await on_event(
                OrchestratorEvent(
                    type=EventType.AGENT_DONE,
                    agent=AgentRole.codeur,
                    ticket_id=ticket_id,
                    data={"content": codeur_result.content},
                )
            )
            self._log(
                f"[{ticket_id}] tour {round_num} — codeur terminé ({codeur_result.duration_ms}ms)"
            )

            await self._ticket_svc.update_status(ticket_id, TicketStatus.in_review)
            await on_event(
                OrchestratorEvent(
                    type=EventType.TICKET_STATUS_CHANGED,
                    ticket_id=ticket_id,
                    data={"status": TicketStatus.in_review.value},
                )
            )

            # --- reviewer ---
            review_context = (
                context
                + f"\n\n## Code produit par le codeur (tour {round_num})\n{codeur_result.content}"
            )

            await on_event(
                OrchestratorEvent(
                    type=EventType.AGENT_STARTED,
                    agent=AgentRole.reviewer,
                    ticket_id=ticket_id,
                    data={"round": round_num},
                )
            )
            self._log(f"[{ticket_id}] tour {round_num} — reviewer démarré")

            reviewer_result = await self._runner.run(
                role=AgentRole.reviewer,
                ticket=ticket,
                project_context=review_context,
                agent_config=reviewer_cfg,
            )
            await on_event(
                OrchestratorEvent(
                    type=EventType.AGENT_DONE,
                    agent=AgentRole.reviewer,
                    ticket_id=ticket_id,
                    data={"content": reviewer_result.content},
                )
            )
            self._log(
                f"[{ticket_id}] tour {round_num} — reviewer terminé ({reviewer_result.duration_ms}ms)"
            )

            approved, reason = _parse_reviewer_verdict(reviewer_result.content)

            if approved:
                await self._ticket_svc.update_status(ticket_id, TicketStatus.done)
                await on_event(
                    OrchestratorEvent(
                        type=EventType.TICKET_STATUS_CHANGED,
                        ticket_id=ticket_id,
                        data={"status": TicketStatus.done.value},
                    )
                )
                await on_event(
                    OrchestratorEvent(
                        type=EventType.PIPELINE_DONE,
                        ticket_id=ticket_id,
                        data={"approved": True, "rounds": round_num},
                    )
                )
                self._log(f"[{ticket_id}] APPROVED après {round_num} tour(s)")
                return PipelineResult(
                    ticket_id=ticket_id,
                    final_status=TicketStatus.done,
                    rounds=round_num,
                    approved=True,
                )

            review_feedback.append(reason or reviewer_result.content[:500])
            self._log(
                f"[{ticket_id}] CHANGES_REQUESTED tour {round_num}: {(reason or '')[:100]}"
            )

        # Max rounds exceeded
        await self._ticket_svc.update_status(ticket_id, TicketStatus.blocked)
        await on_event(
            OrchestratorEvent(
                type=EventType.TICKET_STATUS_CHANGED,
                ticket_id=ticket_id,
                data={"status": TicketStatus.blocked.value},
            )
        )
        await on_event(
            OrchestratorEvent(
                type=EventType.PIPELINE_DONE,
                ticket_id=ticket_id,
                data={"approved": False, "rounds": self._max_review_rounds},
            )
        )
        self._log(
            f"[{ticket_id}] BLOCKED après {self._max_review_rounds} tour(s) sans approbation"
        )
        return PipelineResult(
            ticket_id=ticket_id,
            final_status=TicketStatus.blocked,
            rounds=self._max_review_rounds,
            approved=False,
        )

    async def pick_next_ticket(self, project_id: str) -> Optional[Ticket]:
        todos = await self._ticket_svc.list_tickets(status=TicketStatus.todo)
        done_ids = {
            t.id for t in await self._ticket_svc.list_tickets(status=TicketStatus.done)
        }
        eligible = [t for t in todos if all(dep in done_ids for dep in t.depends_on)]
        if not eligible:
            return None
        return min(eligible, key=lambda t: _PRIORITY_ORDER.get(t.priority, 99))

    async def run_autonomous(
        self,
        project_id: str,
        max_tickets: int = 5,
        on_event: EventCallback | None = None,
    ) -> list[PipelineResult]:
        async def _noop(event: OrchestratorEvent) -> None:
            pass

        callback = on_event or _noop
        results: list[PipelineResult] = []

        for _ in range(max_tickets):
            ticket = await self.pick_next_ticket(project_id)
            if ticket is None:
                break
            result = await self.run_pipeline(project_id, ticket.id, callback)
            results.append(result)

        return results

    def _log(self, message: str) -> None:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        line = f"- {ts} — {message}\n"
        try:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
            with self._log_path.open("a", encoding="utf-8") as f:
                f.write(line)
        except Exception as exc:
            _logger.warning("pipeline_log_write_failed", extra={"error": str(exc)})
