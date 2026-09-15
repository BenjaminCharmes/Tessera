from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from vibe_ide.models.agent import AgentConfig, AgentRole
from vibe_ide.models.ticket import Ticket, TicketPriority, TicketStatus
from vibe_ide.services.agent_runner import AgentRunner
from vibe_ide.services.git_workspace import GitWorkspaceError
from vibe_ide.services.pipeline_events import (
    EventCallback,
    EventType,
    OrchestratorEvent,
    PipelineResult,
)
from vibe_ide.services.pipeline_text import (
    _extract_criteria,
    _parse_reviewer_verdict,
    _single_line,
    _unapproved_commit_message,
)
from vibe_ide.services.ticket_service import TicketService
from vibe_ide.utils.logger import get_logger

if TYPE_CHECKING:
    from vibe_ide.services.doc_updater import DocUpdaterService
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

        # Every pipeline run now commits its own work — approved or not — on
        # its own branch, so a dirty tree at the start of a run is no longer
        # the routine way a rejected run hands off to inspection: it means
        # something *outside* vibe-ide touched the tree between runs. This
        # guard is therefore a safety net, not the isolation mechanism (that
        # job belongs to per-run branches), and should trip rarely. When it
        # does, the ticket must not be left in `todo` — that would make
        # `pick_next_ticket` hand back this exact ticket on every remaining
        # slot of an autonomous run, burning them all on zero progress.
        # Setting it to `blocked` (excluded from `pick_next_ticket`'s
        # `todo`-only selection) lets the queue advance instead.
        if self._git_workspace is not None:
            try:
                if not await self._git_workspace.is_clean():
                    _logger.warning(
                        "dirty_working_tree_refused", extra={"ticket_id": ticket_id}
                    )
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
                            type=EventType.ERROR,
                            ticket_id=ticket_id,
                            data={"reason": "dirty_working_tree"},
                        )
                    )
                    return PipelineResult(
                        ticket_id=ticket_id,
                        final_status=TicketStatus.blocked,
                        rounds=0,
                        approved=False,
                    )
            except GitWorkspaceError as exc:
                _logger.warning("dirty_check_failed", extra={"error": str(exc)})

        await self._ticket_svc.update_status(ticket_id, TicketStatus.in_progress)
        await on_event(
            OrchestratorEvent(
                type=EventType.TICKET_STATUS_CHANGED,
                ticket_id=ticket_id,
                data={"status": TicketStatus.in_progress.value},
            )
        )

        branch: str | None = None
        if self._git_workspace is not None:
            try:
                branch = await self._git_workspace.create_branch(ticket_id, ticket.title)
                await on_event(
                    OrchestratorEvent(
                        type=EventType.BRANCH_CREATED,
                        ticket_id=ticket_id,
                        data={"branch": branch},
                    )
                )
                self._log(f"[{ticket_id}] branche {branch}")
            except GitWorkspaceError as exc:
                # Un projet sans dépôt git reste utilisable : on continue sans
                # garde-fou de branche plutôt que d'interrompre le pipeline.
                # Volontairement restreint à GitWorkspaceError : une erreur de
                # programmation doit remonter, pas finir en avertissement.

                _logger.warning("branch_creation_failed", extra={"error": str(exc)})

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

            # Le codeur écrit réellement sur disque : ce qui doit être relu,
            # audité et validé, c'est le diff, pas la prose de l'agent.
            reviewed_code = codeur_result.content
            if self._git_workspace is not None:
                try:
                    diff = await self._git_workspace.current_diff()
                    if diff.strip():
                        reviewed_code = diff
                    else:
                        _logger.info(
                            "diff_empty_fallback_to_prose", extra={"ticket_id": ticket_id}
                        )
                except GitWorkspaceError as exc:
                    _logger.warning("diff_failed", extra={"error": str(exc)})
                    _logger.info(
                        "diff_empty_fallback_to_prose", extra={"ticket_id": ticket_id}
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
                        code_diff=reviewed_code,
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
                        commit_sha = await self._commit_work(
                            ticket_id,
                            branch,
                            _unapproved_commit_message(
                                ticket_id,
                                f"security block: {_single_line(audit.summary)[:80]}",
                            ),
                            on_event,
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
                            branch=branch,
                            commit_sha=commit_sha,
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
                + f"\n\n## Code produit par le codeur (tour {round_num})\n{reviewed_code}"
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
                            code_produced=reviewed_code,
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
                            diff=reviewed_code,
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

                # This message is written into the *user's* project
                # repository, so it must follow that project's own commit
                # convention — Conventional Commits — using the ticket's own
                # type rather than a hardcoded "feat:", which mislabelled
                # fix/chore/docs tickets. `_commit_work` gates on `branch`
                # too, not just on git_workspace being configured: if
                # create_branch failed above, branch stays None and we must
                # not commit onto whatever ref happened to be checked out.
                commit_sha = await self._commit_work(
                    ticket_id,
                    branch,
                    f"{ticket.type.value}: {ticket_id} — {ticket.title}",
                    on_event,
                )
                # Only an *approved* ticket moves the base ref forward.
                # Isolation-by-branch keeps a rejected ticket's work out of
                # the next ticket; it must not also hide an approved
                # ticket's work from the tickets that follow, or every step
                # of a sequential plan would run against a stale base.
                if commit_sha is not None and self._git_workspace is not None:
                    try:
                        await self._git_workspace.advance_base_ref()
                    except GitWorkspaceError as exc:
                        _logger.warning(
                            "advance_base_ref_failed", extra={"error": str(exc)}
                        )

                return PipelineResult(
                    ticket_id=ticket_id,
                    final_status=TicketStatus.done,
                    rounds=round_num,
                    approved=True,
                    branch=branch,
                    commit_sha=commit_sha,
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
        commit_sha = await self._commit_work(
            ticket_id,
            branch,
            _unapproved_commit_message(
                ticket_id,
                "changes requested — rounds exhausted after "
                f"{self._max_review_rounds} round(s)",
            ),
            on_event,
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
            branch=branch,
            commit_sha=commit_sha,
        )

    async def _commit_work(
        self,
        ticket_id: str,
        branch: str | None,
        message: str,
        on_event: EventCallback,
    ) -> str | None:
        """Commit whatever the coder produced under `message`; emit COMMIT_CREATED.

        Gated on both `git_workspace` being configured and `branch` being
        not None — a failed branch creation must never result in a commit
        onto whatever ref happened to be checked out. Applies on every exit
        path (approved or not): isolation-by-branch relies on each run
        leaving the tree clean for the next one.
        """
        if self._git_workspace is None or branch is None:
            return None
        try:
            commit_sha = await self._git_workspace.commit_all(message)
        except GitWorkspaceError as exc:
            _logger.warning("commit_failed", extra={"error": str(exc)})
            return None
        if commit_sha is not None:
            await on_event(
                OrchestratorEvent(
                    type=EventType.COMMIT_CREATED,
                    ticket_id=ticket_id,
                    data={"sha": commit_sha, "branch": branch},
                )
            )
        return commit_sha

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


__all__ = [
    "EventCallback",
    "EventType",
    "Orchestrator",
    "OrchestratorEvent",
    "PipelineResult",
]
