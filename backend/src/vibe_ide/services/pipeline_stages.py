"""The individual stages of a pipeline run — ticket-046.

`run_pipeline` used to hold all of this inline: some 490 lines chaining
coder → tests → security → reviewer → validator → doc-updater → commit,
over shared local state and event-emitting closures. Each stage now lives in
its own function, so it can be read and tested on its own.

Stages take the `Orchestrator` explicitly rather than living on it: they need
essentially all of its collaborators, and passing it in keeps the dependency
visible instead of hiding it behind a mixin.

A stage that can end the run returns a `PipelineResult`; returning `None`
means "carry on".
"""
from typing import TYPE_CHECKING, Any, Optional

from vibe_ide.models.agent import AgentRole
from vibe_ide.models.ticket import TicketStatus
from vibe_ide.services.git_workspace import GitWorkspaceError
from vibe_ide.services.pipeline_events import (
    EventType,
    OrchestratorEvent,
    PipelineResult,
)
from vibe_ide.services.pipeline_outcomes import finish_security_block
from vibe_ide.services.pipeline_run import PipelineRun, emit, set_status
from vibe_ide.services.pipeline_text import _extract_criteria, _parse_reviewer_verdict
from vibe_ide.utils.logger import get_logger

if TYPE_CHECKING:
    from vibe_ide.services.orchestrator import Orchestrator

_logger = get_logger(__name__)


# ------------------------------------------------------------------
# Préparation
# ------------------------------------------------------------------


async def ensure_clean_tree(
    orch: "Orchestrator", run: PipelineRun
) -> Optional[PipelineResult]:
    """Refuse to start on a tree something outside vibe-ide has modified.

    Every run now commits its own work, approved or not, so a dirty tree is
    no longer how a rejected run hands off for inspection: it means the tree
    changed behind the pipeline's back. The ticket must not be left in
    `todo` — `pick_next_ticket` would hand back this exact ticket on every
    remaining slot of an autonomous run, burning them all on zero progress.
    """
    if orch._git_workspace is None:
        return None
    try:
        if await orch._git_workspace.is_clean():
            return None
    except GitWorkspaceError as exc:
        _logger.warning("dirty_check_failed", extra={"error": str(exc)})
        return None

    _logger.warning("dirty_working_tree_refused", extra={"ticket_id": run.ticket_id})
    await set_status(orch, run, TicketStatus.blocked)
    await emit(run, EventType.ERROR, reason="dirty_working_tree")
    return PipelineResult(
        ticket_id=run.ticket_id,
        final_status=TicketStatus.blocked,
        rounds=0,
        approved=False,
    )


async def create_branch(orch: "Orchestrator", run: PipelineRun) -> None:
    """Switch to the ticket's own branch; degrade without one if git is absent."""
    if orch._git_workspace is None:
        return
    try:
        run.branch = await orch._git_workspace.create_branch(
            run.ticket_id, run.ticket.title
        )
        await emit(run, EventType.BRANCH_CREATED, branch=run.branch)
        orch._log(f"[{run.ticket_id}] branche {run.branch}")
    except GitWorkspaceError as exc:
        # Un projet sans dépôt git reste utilisable : on continue sans
        # garde-fou de branche plutôt que d'interrompre le pipeline.
        # Volontairement restreint à GitWorkspaceError : une erreur de
        # programmation doit remonter, pas finir en avertissement.
        _logger.warning("branch_creation_failed", extra={"error": str(exc)})


def build_context(orch: "Orchestrator", run: PipelineRun) -> str:
    """Project context, reviewer feedback so far, and anything the user said.

    This is where the user's in-flight messages enter the run (ticket-066).
    Every stage builds its context here, so draining the mailbox at this one
    point is what makes an interjection reach *the next agent to speak*, no
    matter which one it is.

    The mailbox is drained, not read: a message injected twice would be
    repeated at every round, and the context would grow a little more each
    time.
    """
    parts = [orch._project_context]

    if run.review_feedback:
        parts.append(
            "\n\n## Retours reviewer précédents\n"
            + "\n---\n".join(
                f"Tour {i + 1}: {fb}" for i, fb in enumerate(run.review_feedback)
            )
        )

    if messages := run.dialogue.drain():
        parts.append(
            "\n\n## Consignes de l'utilisateur, en cours de run\n"
            + "\n".join(f"- {m}" for m in messages)
        )

    return "".join(parts)


# ------------------------------------------------------------------
# Codeur
# ------------------------------------------------------------------


async def run_coder(orch: "Orchestrator", run: PipelineRun, context: str) -> None:
    """Run the coder, then capture what it actually wrote to disk."""
    codeur_cfg = orch._config_for(AgentRole.codeur)
    ticket_id = run.ticket_id

    await run.on_event(
        OrchestratorEvent(
            type=EventType.AGENT_STARTED,
            agent=AgentRole.codeur,
            ticket_id=ticket_id,
            data={"round": run.round_num},
        )
    )
    orch._log(f"[{ticket_id}] tour {run.round_num} — codeur démarré")

    async def _emit_token(token: str, tid: str = ticket_id) -> None:
        await run.on_event(
            OrchestratorEvent(
                type=EventType.AGENT_TOKEN,
                agent=AgentRole.codeur,
                ticket_id=tid,
                data={"token": token},
            )
        )

    async def _emit_tool(name: str, payload: dict[str, Any], tid: str = ticket_id) -> None:
        await run.on_event(
            OrchestratorEvent(
                type=EventType.AGENT_TOOL_USE,
                agent=AgentRole.codeur,
                ticket_id=tid,
                data={"tool": name, "input": payload},
            )
        )

    codeur_result = await orch._runner.run(
        role=AgentRole.codeur,
        ticket=run.ticket,
        project_context=context,
        agent_config=codeur_cfg,
        stream_callback=_emit_token,
        tool_callback=_emit_tool,
        run_id=run.run_id,
    )
    orch.record_spend(codeur_result.cost_usd)
    await run.on_event(
        OrchestratorEvent(
            type=EventType.AGENT_DONE,
            agent=AgentRole.codeur,
            ticket_id=ticket_id,
            data={"content": codeur_result.content},
        )
    )
    orch._log(
        f"[{ticket_id}] tour {run.round_num} — codeur terminé ({codeur_result.duration_ms}ms)"
    )

    run.reviewed_code = await _capture_diff(orch, run, codeur_result.content)
    await set_status(orch, run, TicketStatus.in_review)


async def _capture_diff(orch: "Orchestrator", run: PipelineRun, prose: str) -> str:
    """The real diff if there is one, the coder's prose as a last resort.

    Le codeur écrit réellement sur disque : ce qui doit être relu, audité et
    validé, c'est le diff, pas la prose de l'agent.
    """
    if orch._git_workspace is None:
        return prose
    try:
        diff = await orch._git_workspace.current_diff()
    except GitWorkspaceError as exc:
        _logger.warning("diff_failed", extra={"error": str(exc)})
        _logger.info("diff_empty_fallback_to_prose", extra={"ticket_id": run.ticket_id})
        return prose
    if diff.strip():
        return diff
    _logger.info("diff_empty_fallback_to_prose", extra={"ticket_id": run.ticket_id})
    return prose


# ------------------------------------------------------------------
# Testeur
# ------------------------------------------------------------------


async def run_tests(orch: "Orchestrator", run: PipelineRun) -> None:
    """Run the project's own test suite and stash its summary for the reviewer."""
    if not (orch._test_runner and orch._project_path):
        return

    from vibe_ide.services.test_runner import TestCommandNotFound

    try:
        result = await orch._test_runner.run_tests(
            orch._project_path, test_command=orch._test_command
        )
        run.test_result = result
        await emit(
            run,
            EventType.TEST_RESULT,
            passed=result.passed,
            total=result.total,
            failed=result.failed,
            output_summary=result.output_summary,
            duration_ms=result.duration_ms,
        )
        badge = "✅" if result.passed else "❌"
        errors = "\nErreurs:\n" + "\n".join(result.errors) if result.errors else ""
        run.test_context = (
            f"\n\n## Résultats des tests {badge}\n{result.output_summary}\n{errors}"
        )
        orch._log(f"[{run.ticket_id}] testeur: {result.output_summary}")
    except TestCommandNotFound:
        orch._log(f"[{run.ticket_id}] testeur: commande non détectée, ignoré")
    except Exception as exc:
        _logger.warning("test_runner_failed", extra={"error": str(exc)})


# ------------------------------------------------------------------
# Sécurité
# ------------------------------------------------------------------


async def run_security_audit(
    orch: "Orchestrator", run: PipelineRun
) -> Optional[PipelineResult]:
    """Audit the diff. A CRITICAL/HIGH verdict ends the run before the reviewer."""
    if not (orch._security_auditor and orch._project_path):
        return None

    await emit(run, EventType.SECURITY_AUDIT_STARTED, round=run.round_num)
    try:
        audit = await orch._security_auditor.audit(
            code_diff=run.reviewed_code, project_path=orch._project_path
        )
    except Exception as exc:
        _logger.warning("security_auditor_failed", extra={"error": str(exc)})
        return None

    await emit(
        run,
        EventType.SECURITY_AUDIT_DONE,
        verdict=audit.verdict,
        issues_count=len(audit.issues),
        has_critical=audit.has_critical,
        has_high=audit.has_high,
        summary=audit.summary,
    )
    orch._log(f"[{run.ticket_id}] securite: {audit.verdict} — {audit.summary[:80]}")

    if audit.verdict == "BLOCK":
        return await finish_security_block(orch, run, audit.summary)

    # PASS — les MEDIUM/LOW remontent au reviewer comme avertissements.
    if audit.issues:
        warnings = "\n".join(
            f"- [{i.severity}] {i.type} @ {i.location}: {i.description}"
            for i in audit.issues
        )
        run.security_context = f"\n\n## Audit sécurité (avertissements)\n{warnings}"
    return None


# ------------------------------------------------------------------
# Reviewer et validateur
# ------------------------------------------------------------------


async def run_review(
    orch: "Orchestrator", run: PipelineRun, context: str
) -> tuple[bool, str, str]:
    """Review the diff. Returns (approved, reason, raw verdict text)."""
    reviewer_cfg = orch._config_for(AgentRole.reviewer)
    ticket_id = run.ticket_id

    review_context = (
        context
        + f"\n\n## Code produit par le codeur (tour {run.round_num})\n{run.reviewed_code}"
        + run.test_context
        + run.security_context
    )

    await run.on_event(
        OrchestratorEvent(
            type=EventType.AGENT_STARTED,
            agent=AgentRole.reviewer,
            ticket_id=ticket_id,
            data={"round": run.round_num},
        )
    )
    orch._log(f"[{ticket_id}] tour {run.round_num} — reviewer démarré")

    reviewer_result = await orch._runner.run(
        role=AgentRole.reviewer,
        ticket=run.ticket,
        project_context=review_context,
        agent_config=reviewer_cfg,
        run_id=run.run_id,
    )
    orch.record_spend(reviewer_result.cost_usd)
    await run.on_event(
        OrchestratorEvent(
            type=EventType.AGENT_DONE,
            agent=AgentRole.reviewer,
            ticket_id=ticket_id,
            data={"content": reviewer_result.content},
        )
    )
    orch._log(
        f"[{ticket_id}] tour {run.round_num} — reviewer terminé ({reviewer_result.duration_ms}ms)"
    )

    approved, reason = _parse_reviewer_verdict(reviewer_result.content)
    return approved, reason, reviewer_result.content


async def run_validation(
    orch: "Orchestrator", run: PipelineRun, reason: str
) -> tuple[bool, str]:
    """Check the ticket's acceptance criteria; may overturn an approval."""
    if orch._validator is None:
        return True, reason
    try:
        validation = await orch._validator.validate(
            criteria=_extract_criteria(run.ticket.body),
            code_produced=run.reviewed_code,
            test_result=run.test_result,
        )
    except Exception as exc:
        _logger.warning("validator_failed", extra={"error": str(exc)})
        return True, reason

    await emit(
        run,
        EventType.VALIDATION_DONE,
        verdict=validation.verdict,
        all_passed=validation.all_passed,
        feedback=validation.feedback,
        criteria=[
            {"criterion": c.criterion, "passed": c.passed, "note": c.note}
            for c in validation.criteria
        ],
    )
    orch._log(
        f"[{run.ticket_id}] validateur: {validation.verdict} — {validation.feedback[:80]}"
    )
    if validation.verdict == "CHANGES_REQUESTED":
        return False, validation.feedback
    return True, reason


async def run_doc_update(orch: "Orchestrator", run: PipelineRun) -> None:
    """Update the project's own documentation from the approved diff."""
    if not (orch._doc_updater and orch._project_path):
        return
    try:
        doc_result = await orch._doc_updater.update_docs(
            orch._project_path,
            diff=run.reviewed_code,
            ticket_title=f"{run.ticket.type.value}: {run.ticket.title}",
        )
        await emit(
            run,
            EventType.DOC_UPDATED,
            files_updated=doc_result.files_updated,
            no_changes=doc_result.no_changes,
        )
        orch._log(
            f"[{run.ticket_id}] doc-updater: {doc_result.files_updated or 'no changes'}"
        )
    except Exception as exc:
        _logger.warning("doc_updater_failed", extra={"error": str(exc)})
