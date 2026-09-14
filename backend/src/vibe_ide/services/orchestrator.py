from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from pydantic import BaseModel, Field

from vibe_ide.models.agent import AgentConfig, AgentRole
from vibe_ide.models.ticket import Ticket, TicketPriority, TicketStatus
from vibe_ide.services.agent_runner import AgentRunner
from vibe_ide.services.ticket_service import TicketService
from vibe_ide.utils.logger import get_logger

if TYPE_CHECKING:
    from vibe_ide.services.doc_updater import DocUpdaterService
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


class EventType(str, Enum):
    AGENT_STARTED = "agent_started"
    AGENT_TOKEN = "agent_token"
    AGENT_TOOL_USE = "agent_tool_use"
    AGENT_DONE = "agent_done"
    TICKET_STATUS_CHANGED = "ticket_status_changed"
    PIPELINE_DONE = "pipeline_done"
    ERROR = "error"
    TEST_RESULT = "test_result"
    SECURITY_AUDIT_STARTED = "security_audit_started"
    SECURITY_AUDIT_DONE = "security_audit_done"
    VALIDATION_DONE = "validation_done"
    DOC_UPDATED = "doc_updated"


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


def _extract_criteria(ticket_body: str) -> list[str]:
    """Extracts acceptance criteria checkboxes from ticket markdown body."""
    import re

    criteria: list[str] = []
    in_criteria_section = False
    for line in ticket_body.splitlines():
        if re.search(r"##\s*(critères|acceptance criteria)", line, re.IGNORECASE):
            in_criteria_section = True
            continue
        if in_criteria_section:
            if line.startswith("##"):
                break
            m = re.match(r"\s*-\s*\[[ xX]?\]\s*(.+)", line)
            if m:
                criteria.append(m.group(1).strip())
    return criteria


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
        doc_updater: Optional["DocUpdaterService"] = None,
        test_runner: Optional["TestRunnerService"] = None,
        test_command: Optional[str] = None,
        security_auditor: Optional["SecurityAuditorService"] = None,
        validator: Optional["ValidatorService"] = None,
        project_path: Optional[Path] = None,
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

            async def _emit_tool(name: str, payload: dict[str, Any], tid: str = ticket_id) -> None:
                await on_event(
                    OrchestratorEvent(
                        type=EventType.AGENT_TOOL_USE,
                        agent=AgentRole.codeur,
                        ticket_id=tid,
                        data={"tool": name, "input": payload},
                    )
                )

            codeur_result = await self._runner.run(
                role=AgentRole.codeur,
                ticket=ticket,
                project_context=context,
                agent_config=codeur_cfg,
                stream_callback=_emit_token,
                tool_callback=_emit_tool,
                run_id=run_id,
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

            # --- testeur (optional) ---
            test_context_block = ""
            security_context_block = ""
            test_result = None
            if self._test_runner and self._project_path:
                try:
                    from vibe_ide.services.test_runner import TestCommandNotFound

                    test_result = await self._test_runner.run_tests(
                        self._project_path,
                        test_command=self._test_command,
                    )
                    await on_event(
                        OrchestratorEvent(
                            type=EventType.TEST_RESULT,
                            ticket_id=ticket_id,
                            data={
                                "passed": test_result.passed,
                                "total": test_result.total,
                                "failed": test_result.failed,
                                "output_summary": test_result.output_summary,
                                "duration_ms": test_result.duration_ms,
                            },
                        )
                    )
                    badge = "✅" if test_result.passed else "❌"
                    test_context_block = (
                        f"\n\n## Résultats des tests {badge}\n"
                        f"{test_result.output_summary}\n"
                        + (
                            "\nErreurs:\n" + "\n".join(test_result.errors)
                            if test_result.errors
                            else ""
                        )
                    )
                    self._log(
                        f"[{ticket_id}] testeur: {test_result.output_summary}"
                    )
                except TestCommandNotFound:
                    self._log(f"[{ticket_id}] testeur: commande non détectée, ignoré")
                except Exception as exc:
                    _logger.warning("test_runner_failed", extra={"error": str(exc)})

            # --- securite (optional) ---
            security_context_block = ""
            if self._security_auditor and self._project_path:
                await on_event(
                    OrchestratorEvent(
                        type=EventType.SECURITY_AUDIT_STARTED,
                        ticket_id=ticket_id,
                        data={"round": round_num},
                    )
                )
                try:
                    audit = await self._security_auditor.audit(
                        code_diff=codeur_result.content,
                        project_path=self._project_path,
                    )
                    await on_event(
                        OrchestratorEvent(
                            type=EventType.SECURITY_AUDIT_DONE,
                            ticket_id=ticket_id,
                            data={
                                "verdict": audit.verdict,
                                "issues_count": len(audit.issues),
                                "has_critical": audit.has_critical,
                                "has_high": audit.has_high,
                                "summary": audit.summary,
                            },
                        )
                    )
                    self._log(
                        f"[{ticket_id}] securite: {audit.verdict} — {audit.summary[:80]}"
                    )
                    if audit.verdict == "BLOCK":
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
                                data={"approved": False, "rounds": round_num, "reason": "security_block"},
                            )
                        )
                        return PipelineResult(
                            ticket_id=ticket_id,
                            final_status=TicketStatus.blocked,
                            rounds=round_num,
                            approved=False,
                        )
                    # PASS — include audit context for reviewer (MEDIUM/LOW as warnings)
                    if audit.issues:
                        warnings = "\n".join(
                            f"- [{i.severity}] {i.type} @ {i.location}: {i.description}"
                            for i in audit.issues
                        )
                        security_context_block = f"\n\n## Audit sécurité (avertissements)\n{warnings}"
                except Exception as exc:
                    _logger.warning("security_auditor_failed", extra={"error": str(exc)})

            # --- reviewer ---
            review_context = (
                context
                + f"\n\n## Code produit par le codeur (tour {round_num})\n{codeur_result.content}"
                + test_context_block
                + security_context_block
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
                run_id=run_id,
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
                # --- validateur (optional) — peut court-circuiter l'approbation ---
                if self._validator:
                    try:
                        criteria = _extract_criteria(ticket.body)
                        validation = await self._validator.validate(
                            criteria=criteria,
                            code_produced=codeur_result.content,
                            test_result=test_result,
                        )
                        await on_event(
                            OrchestratorEvent(
                                type=EventType.VALIDATION_DONE,
                                ticket_id=ticket_id,
                                data={
                                    "verdict": validation.verdict,
                                    "all_passed": validation.all_passed,
                                    "feedback": validation.feedback,
                                    "criteria": [
                                        {"criterion": c.criterion, "passed": c.passed, "note": c.note}
                                        for c in validation.criteria
                                    ],
                                },
                            )
                        )
                        self._log(
                            f"[{ticket_id}] validateur: {validation.verdict} — {validation.feedback[:80]}"
                        )
                        if validation.verdict == "CHANGES_REQUESTED":
                            approved = False
                            reason = validation.feedback
                    except Exception as exc:
                        _logger.warning("validator_failed", extra={"error": str(exc)})

            if approved:
                # --- doc-updater (optional) ---
                if self._doc_updater and self._project_path:
                    try:
                        doc_result = await self._doc_updater.update_docs(
                            self._project_path,
                            diff=codeur_result.content,
                            ticket_title=f"{ticket.type.value}: {ticket.title}",
                        )
                        await on_event(
                            OrchestratorEvent(
                                type=EventType.DOC_UPDATED,
                                ticket_id=ticket_id,
                                data={
                                    "files_updated": doc_result.files_updated,
                                    "no_changes": doc_result.no_changes,
                                },
                            )
                        )
                        self._log(
                            f"[{ticket_id}] doc-updater: {doc_result.files_updated or 'no changes'}"
                        )
                    except Exception as exc:
                        _logger.warning("doc_updater_failed", extra={"error": str(exc)})

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
