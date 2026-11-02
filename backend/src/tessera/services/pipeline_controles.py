"""Stages — security audit, review and validation (ticket-688, split from
`pipeline_stages`).

Each gate fails closed: an exception from the auditor or the validator is a
refusal, never a pass — except an exhausted quota, which must reach
`run_pipeline` (ticket-498).
"""
import time
from typing import TYPE_CHECKING, Optional

from tessera.models.agent import AgentRole
from tessera.services.config_tests_touchee import (
    avertissement_config_tests,
    config_tests_du_diff,
    porte_config_nommee,
)
from tessera.services.pipeline_events import (
    EventType,
    OrchestratorEvent,
    PipelineResult,
)
from tessera.services.pipeline_outcomes import finish_security_block
from tessera.services.pipeline_run import PipelineRun, emit
from tessera.services.pipeline_text import _extract_criteria
from tessera.services.quota_exhaustion import is_quota_exhausted
from tessera.services.reviewer_schema import REVIEWER_SCHEMA
from tessera.services.security_auditor import SecurityAuditResult
from tessera.services.validator_cited_files import format_cited_files_log
from tessera.services.validator_decisions import validator_extras
from tessera.services.verdict_reviewer import donnees_fin_de_revue, juger_revue
from tessera.utils.logger import get_logger

if TYPE_CHECKING:
    from tessera.services.orchestrator import Orchestrator

_logger = get_logger(__name__)


def _quota_epuise(orch: "Orchestrator", exc: BaseException) -> bool:
    """True when ``exc`` is an exhausted quota, read with the last snapshot.

    Such an exception must reach `run_pipeline`, which ends the run as a quota
    stop (ticket-498) ; any other failure keeps the closed-fail verdict.
    """
    # `getattr` : les doubles d'orchestrateur des tests d'étape n'ont pas de quota.
    tracker = getattr(orch, "quota", None)
    return is_quota_exhausted(exc, tracker.snapshot if tracker is not None else None)


async def run_security_audit(
    orch: "Orchestrator", run: PipelineRun
) -> Optional[PipelineResult]:
    """Audit the diff. A CRITICAL/HIGH verdict ends the run before the reviewer.

    Échoue fermé : une exception de l'auditeur sautait l'audit et le diff
    arrivait au reviewer comme s'il était propre (ticket-122).
    """
    if not (orch._security_auditor and orch._project_path):
        return None

    await emit(run, EventType.SECURITY_AUDIT_STARTED, round=run.round_num)
    t0 = time.monotonic()
    try:
        audit = await orch._security_auditor.audit(
            code_diff=run.reviewed_code, project_path=orch._project_path
        )
    except Exception as exc:
        if _quota_epuise(orch, exc):
            raise
        _logger.warning("security_auditor_failed", extra={"error": str(exc)})
        reason = f"Audit sécurité en panne : {exc}"
        audit = SecurityAuditResult(
            issues=[], verdict="BLOCK", summary=reason, reason=reason
        )
    audit_ms = int((time.monotonic() - t0) * 1000)

    if audit.fallback_reason:
        await emit(
            run, EventType.SECURITY_AUDIT_FALLBACK, reason=audit.fallback_reason
        )
    await emit(
        run,
        EventType.SECURITY_AUDIT_DONE,
        verdict=audit.verdict,
        issues_count=len(audit.issues),
        has_critical=audit.has_critical,
        has_high=audit.has_high,
        summary=audit.summary,
        reason=audit.reason,
    )
    orch._log(
        f"[{run.ticket_id}] securite: {audit.verdict} — {audit.summary[:80]} ({audit_ms}ms)"
    )

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

    # Le journal nomme les fichiers : le signal survit à la réponse du reviewer.
    config_touchee = config_tests_du_diff(
        run.reviewed_code, orch._project_path,
        lambda ligne: orch._log(f"[{ticket_id}] {ligne}"),
    )
    review_context = (
        avertissement_config_tests(config_touchee)
        + context
        + f"\n\n## Code produit par le codeur (tour {run.round_num})\n{run.reviewed_code}"
        + run.artifact_diff
        + run.refus_du_tour
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
        schema=REVIEWER_SCHEMA,
    )
    orch.record_spend(reviewer_result.cost_usd)
    approved, reason, review_text = porte_config_nommee(
        juger_revue(reviewer_result.structured), config_touchee,
        f"{run.ticket.title}\n{run.ticket.body}",
        lambda ligne: orch._log(f"[{ticket_id}] {ligne}"),
    )
    await run.on_event(
        OrchestratorEvent(
            type=EventType.AGENT_DONE,
            agent=AgentRole.reviewer,
            ticket_id=ticket_id,
            data=donnees_fin_de_revue(approved, review_text, reviewer_result),
        )
    )
    orch._log(
        f"[{ticket_id}] tour {run.round_num} — reviewer terminé ({reviewer_result.duration_ms}ms)"
    )

    return approved, reason, review_text


async def run_validation(
    orch: "Orchestrator", run: PipelineRun
) -> tuple[bool, str]:
    """Check the ticket's acceptance criteria independently of the reviewer.

    Returns ``(True, "")`` when the validator is absent or approves,
    ``(False, feedback)`` when it refuses or is unavailable.
    """
    if orch._validator is None:
        return True, ""
    await emit(run, EventType.VALIDATION_STARTED)
    t0 = time.monotonic()
    # Refus du garde-fou et réponses du dialogue, seulement s'il y en a.
    extra = validator_extras(run.refus_du_tour, run.dialogue)
    try:
        validation = await orch._validator.validate(
            criteria=_extract_criteria(run.ticket.body),
            code_produced=run.reviewed_code + run.artifact_diff,
            test_result=run.test_result,
            project_root=orch._project_path,
            ticket_type=run.ticket.type,
            **extra,
        )
    except Exception as exc:
        if _quota_epuise(orch, exc):
            raise
        # Échoue fermé, comme l'audit : une validation qui n'a pas eu lieu
        # n'approuve rien (ticket-122).
        _logger.warning("validator_failed", extra={"error": str(exc)})
        return False, f"Validation en panne : {exc}"
    validation_ms = int((time.monotonic() - t0) * 1000)

    await emit(
        run,
        EventType.VALIDATION_DONE,
        verdict=validation.verdict,
        # Le frontend lit `approved` pour afficher le statut ; le fallback sur
        # `verdict` existe côté frontend, mais le champ explicite est plus fiable
        # (ticket-279).
        approved=(validation.verdict == "APPROVED"),
        all_passed=validation.all_passed,
        feedback=validation.feedback,
        criteria=[
            {"criterion": c.criterion, "passed": c.passed, "note": c.note}
            for c in validation.criteria
        ],
    )
    if validation.cited_files is not None:
        cited_line = format_cited_files_log(validation.cited_files)
        if cited_line:
            orch._log(f"[{run.ticket_id}] {cited_line}")
    orch._log(
        f"[{run.ticket_id}] validateur: {validation.verdict} — "
        f"{validation.feedback[:80]} ({validation_ms}ms)"
    )
    if validation.verdict == "CHANGES_REQUESTED":
        return False, validation.feedback
    return True, ""
