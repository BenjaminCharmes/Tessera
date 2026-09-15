"""Pipeline orchestration — the sequence only.

Each stage lives in `pipeline_stages.py`; this module chains them and owns
the early exits. Keeping the flow readable in one screen is the point: the
order of the stages, and the conditions that end a run, are the part that is
hard to get right.
"""
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from vibe_ide.models.agent import AgentConfig, AgentRole
from vibe_ide.models.ticket import Ticket, TicketPriority, TicketStatus
from vibe_ide.services.agent_runner import AgentRunner
from vibe_ide.services.pipeline_events import (
    EventCallback,
    EventType,
    OrchestratorEvent,
    PipelineResult,
)
from vibe_ide.services.ticket_service import TicketService
from vibe_ide.utils.logger import get_logger

from vibe_ide.services import pipeline_outcomes as outcomes
from vibe_ide.services import pipeline_stages as stages
from vibe_ide.services.pipeline_run import PipelineRun, set_status

if TYPE_CHECKING:
    from vibe_ide.services.doc_updater import DocUpdaterService
    from vibe_ide.services.quota_tracker import QuotaTracker
    from vibe_ide.services.git_workspace import GitWorkspaceService
    from vibe_ide.services.security_auditor import SecurityAuditorService
    from vibe_ide.services.test_runner import TestRunnerService
    from vibe_ide.services.validator import ValidatorService

_logger = get_logger(__name__)

_PRIORITY_ORDER: dict[TicketPriority, int] = {
    TicketPriority.critical: 0,
    TicketPriority.high: 1,
    TicketPriority.medium: 2,
    TicketPriority.low: 3,
}


class Orchestrator:
    def __init__(
        self,
        runner: AgentRunner,
        ticket_service: TicketService,
        project_context: str,
        agent_configs: list[AgentConfig],
        pipeline_log_path: Path,
        max_review_rounds: int = 3,
        doc_updater: Optional["DocUpdaterService"] = None,
        test_runner: Optional["TestRunnerService"] = None,
        test_command: Optional[str] = None,
        security_auditor: Optional["SecurityAuditorService"] = None,
        validator: Optional["ValidatorService"] = None,
        project_path: Optional[Path] = None,
        git_workspace: Optional["GitWorkspaceService"] = None,
        run_max_budget_usd: float = 0.0,
        quota_tracker: Optional["QuotaTracker"] = None,
    ) -> None:
        self._runner = runner
        self._ticket_svc = ticket_service
        self._project_context = project_context
        self._agent_configs = agent_configs
        self._log_path = pipeline_log_path
        self._max_review_rounds = max_review_rounds
        self._doc_updater = doc_updater
        self._test_runner = test_runner
        self._test_command = test_command
        self._security_auditor = security_auditor
        self._validator = validator
        self._project_path = project_path
        self._git_workspace = git_workspace
        self._run_max_budget_usd = run_max_budget_usd
        self._spent_usd = 0.0
        # Le quota d'abonnement est la ressource réellement finie en mode
        # `agent_sdk` : la dépense estimée de ticket-052 ne la mesure pas.
        self._quota_tracker = quota_tracker

    @property
    def quota(self) -> Optional["QuotaTracker"]:
        return self._quota_tracker

    @property
    def spent_usd(self) -> float:
        """Cumulative spend since this orchestrator was built."""
        return round(self._spent_usd, 10)

    def record_spend(self, cost_usd: float) -> None:
        """Add one agent call's cost to the run's running total."""
        self._spent_usd += cost_usd or 0.0

    def budget_exhausted(self) -> bool:
        """True once the run has spent its ceiling. `0` means no ceiling."""
        if self._run_max_budget_usd <= 0:
            return False
        return self._spent_usd >= self._run_max_budget_usd

    def _config_for(self, role: AgentRole) -> Optional[AgentConfig]:
        return next((c for c in self._agent_configs if c.role == role.value), None)

    async def run_pipeline(
        self,
        project_id: str,
        ticket_id: str,
        on_event: EventCallback,
        run_id: str | None = None,
    ) -> PipelineResult:
        ticket = await self._ticket_svc.get_ticket(ticket_id)
        if ticket is None:
            raise ValueError(f"Ticket introuvable : {ticket_id}")

        run = PipelineRun(
            project_id=project_id, ticket=ticket, on_event=on_event, run_id=run_id
        )

        refused = await stages.ensure_clean_tree(self, run)
        if refused is not None:
            return refused

        await set_status(self, run, TicketStatus.in_progress)
        await stages.create_branch(self, run)

        for round_num in range(1, self._max_review_rounds + 1):
            run.start_round(round_num)
            context = stages.build_context(self, run)

            await stages.run_coder(self, run, context)
            await stages.run_tests(self, run)

            blocked = await stages.run_security_audit(self, run)
            if blocked is not None:
                return blocked

            approved, reason, raw_verdict = await stages.run_review(self, run, context)

            if approved:
                # Le validateur peut court-circuiter l'approbation du reviewer.
                approved, reason = await stages.run_validation(self, run, reason)

            if approved:
                await stages.run_doc_update(self, run)
                return await outcomes.finish_approved(self, run)

            run.review_feedback.append(reason or raw_verdict[:500])
            self._log(
                f"[{ticket_id}] CHANGES_REQUESTED tour {round_num}: {(reason or '')[:100]}"
            )

        return await outcomes.finish_rounds_exhausted(self, run)

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
            # Le plafond est vérifié *entre* les tickets : interrompre un
            # ticket en cours laisserait son travail non commité, ce que
            # l'isolation par branche interdit (ADR-018).
            if self.budget_exhausted():
                _logger.warning(
                    "run_budget_exhausted",
                    extra={
                        "spent_usd": self.spent_usd,
                        "max_usd": self._run_max_budget_usd,
                    },
                )
                self._log(
                    f"[{project_id}] run interrompu : {self.spent_usd:.2f} USD "
                    f"dépensés sur {self._run_max_budget_usd:.2f} autorisés"
                )
                break

            # Seconde condition d'arrêt : le quota réel de l'abonnement. Un
            # quota inconnu ne bloque pas — un provider muet doit rester
            # indiscernable d'un quota confortable (ticket-054).
            if self._quota_tracker is not None and self._quota_tracker.is_low():
                snapshot = self._quota_tracker.snapshot
                _logger.warning(
                    "run_quota_low",
                    extra={"utilization": snapshot.utilization if snapshot else None},
                )
                self._log(
                    f"[{project_id}] run interrompu : quota d'abonnement à "
                    f"{(snapshot.utilization * 100) if snapshot else 0:.0f} %"
                )
                await callback(
                    OrchestratorEvent(
                        type=EventType.QUOTA_UPDATED,
                        ticket_id="",
                        data={
                            **self._quota_tracker.as_event_data(),
                            "run_interrupted": True,
                        },
                    )
                )
                break

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


__all__ = [
    "EventCallback",
    "EventType",
    "Orchestrator",
    "OrchestratorEvent",
    "PipelineResult",
]
