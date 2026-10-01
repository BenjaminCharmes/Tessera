"""The individual stages of a pipeline run — ticket-046.

`run_pipeline` used to hold all of this inline: some 490 lines chaining
coder → tests → security → reviewer → validator → documentation → commit,
over shared local state and event-emitting closures. Each stage now lives in
its own function, so it can be read and tested on its own.

Stages take the `Orchestrator` explicitly rather than living on it: they need
essentially all of its collaborators, and passing it in keeps the dependency
visible instead of hiding it behind a mixin.

A stage that can end the run returns a `PipelineResult`; returning `None`
means "carry on".
"""
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, Optional

from tessera.models.agent import AgentRole
from tessera.models.ticket import TicketStatus, TicketType
from tessera.services.artifact_snapshot import diff_artifacts, snapshot_artifacts
from tessera.services.git_workspace import GitWorkspaceError
from tessera.services.pipeline_events import (
    EventType,
    OrchestratorEvent,
    PipelineResult,
)
from tessera.services.pipeline_outcomes import finish_security_block
from tessera.services.pipeline_run import PipelineRun, emit, set_status
from tessera.services.pipeline_text import _extract_criteria, _parse_reviewer_verdict
from tessera.services.security_auditor import SecurityAuditResult
from tessera.utils.logger import get_logger

if TYPE_CHECKING:
    from tessera.services.orchestrator import Orchestrator

_logger = get_logger(__name__)


# ------------------------------------------------------------------
# Préparation
# ------------------------------------------------------------------


async def ensure_clean_tree(
    orch: "Orchestrator", run: PipelineRun
) -> Optional[PipelineResult]:
    """Refuse to start on a tree something outside Tessera has modified.

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


def take_artifact_snapshot(orch: "Orchestrator", run: PipelineRun) -> None:
    """Take a snapshot of memory/ and tickets/ before any agent runs.

    Stored in ``run.artifact_snapshot`` and used at the end of each coder turn
    to produce the artifact diff — a textual view of what the agent wrote in
    Tessera's own directories, which are excluded from the git diff either
    because the project is in local-artifact mode (ADR-021) or because
    ``_ORCHESTRATOR_ARTIFACT_PATHS`` excludes them from the reviewed diff.

    Called once per run, before the first tour.  No-op when no project path is
    configured (tests, projects without a filesystem path).
    """
    if orch._project_path is None:
        return
    run.artifact_snapshot = snapshot_artifacts(orch._project_path)


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

    # Le plan précède les retours : le codeur le suit, le reviewer juge
    # l'écart (ticket-243). Il reste dans le contexte du tour, donc dans les
    # reprises : c'est court, et c'est ce qui dit où le travail doit aller.
    if run.plan:
        parts.append(f"\n\n## Plan retenu avant le code\n{run.plan}")

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

    # Gardé à part pour le codeur qui reprend sa session (ticket-187) : la
    # boîte aux lettres est vidée ici, une seconde construction ne retrouverait
    # plus les consignes.
    run.contexte_du_tour = "".join(parts[1:]).strip()
    return "".join(parts)


def asker_for(run: PipelineRun) -> Optional[Callable[[str], Awaitable[str]]]:
    """L'outil `ask_user` à donner à l'agent, ou rien (ticket-066).

    Un run non interactif — appel programmatique, test, run autonome — ne doit
    pas recevoir l'outil : l'agent y attendrait le délai complet d'ADR-025 à
    chaque question, sans que personne ne puisse jamais y répondre.
    """
    return run.dialogue.ask if run.dialogue.interactive else None


# ------------------------------------------------------------------
# Codeur
# ------------------------------------------------------------------


async def run_coder(orch: "Orchestrator", run: PipelineRun, context: str) -> None:
    """Run the coder, then capture what it actually wrote to disk."""
    # Un ticket `design` ne demande pas du code mais une décision, et
    # `ide-core/CLAUDE.md` promettait l'architecte dessus depuis le premier
    # commit sans que rien ne route par type (ticket-098). L'étape reste la
    # même — quelqu'un produit le travail — seul le rôle change. Les
    # événements portent ce rôle, pas `codeur` en dur : l'UI montrait un
    # codeur au travail quand l'architecte produisait (ticket-122).
    role = _role_qui_produit(run.ticket.type)
    codeur_cfg = orch._config_for(role)
    ticket_id = run.ticket_id

    await run.on_event(
        OrchestratorEvent(
            type=EventType.AGENT_STARTED,
            agent=role,
            ticket_id=ticket_id,
            data={"round": run.round_num},
        )
    )
    orch._log(f"[{ticket_id}] tour {run.round_num} — codeur démarré")

    async def _emit_token(token: str, tid: str = ticket_id) -> None:
        await run.on_event(
            OrchestratorEvent(
                type=EventType.AGENT_TOKEN,
                agent=role,
                ticket_id=tid,
                data={"token": token},
            )
        )

    async def _emit_tool(name: str, payload: dict[str, Any], tid: str = ticket_id) -> None:
        await run.on_event(
            OrchestratorEvent(
                type=EventType.AGENT_TOOL_USE,
                agent=role,
                ticket_id=tid,
                data={"tool": name, "input": payload},
            )
        )

    # Comme au niveau du provider : le paramètre n'est transmis que s'il y a
    # quelque chose à transmettre. Un run non interactif appelle donc le
    # runner exactement comme avant ce ticket.
    asker = asker_for(run)
    extra: dict[str, Any] = {"ask_user": asker} if asker is not None else {}

    # Au tour suivant, le codeur reprend sa conversation et ne reçoit que ce
    # que le tour ajoute : le ticket, les ADR et le dépôt, il les a déjà lus
    # (ticket-187). Sans session — premier tour, provider muet — l'appel
    # reste complet.
    if run.session_codeur is not None:
        extra["session"] = run.session_codeur
        context = run.contexte_du_tour
    elif run.carte_du_depot:
        # La carte précède le contexte : `adr_pertinents` découpe tout ce qui
        # suit « Décisions récentes » en ADR, et une carte placée après serait
        # avalée par le dernier d'entre eux (ticket-190). Le reviewer ne la
        # reçoit pas : il part du diff.
        context = (
            "## Fichiers du projet\n"
            "Lis ce dont tu as besoin ; ne relis pas cette carte.\n\n"
            f"{run.carte_du_depot}\n\n{context}"
        )

    codeur_result = await orch._runner.run(
        role=role,
        ticket=run.ticket,
        project_context=context,
        agent_config=codeur_cfg,
        stream_callback=_emit_token,
        tool_callback=_emit_tool,
        run_id=run.run_id,
        **extra,
    )
    if codeur_result.session_id is not None:
        run.session_codeur = codeur_result.session_id
    orch.record_spend(codeur_result.cost_usd)
    await run.on_event(
        OrchestratorEvent(
            type=EventType.AGENT_DONE,
            agent=role,
            ticket_id=ticket_id,
            # Le coût part avec la fin de l'appel : c'est pendant le run
            # qu'on décide de l'arrêter (ticket-197).
            data={
                "content": codeur_result.content,
                "cost_usd": codeur_result.cost_usd,
                "duration_ms": codeur_result.duration_ms,
            },
        )
    )
    orch._log(
        f"[{ticket_id}] tour {run.round_num} — {role.value} terminé "
        f"({codeur_result.duration_ms}ms)"
    )

    run.reviewed_code = await _capture_diff(orch, run, codeur_result.content)
    _capture_artifact_diff(orch, run)
    await set_status(orch, run, TicketStatus.in_review)


async def _capture_diff(orch: "Orchestrator", run: PipelineRun, prose: str) -> str:
    """The real diff if there is one, the coder's prose as a last resort.

    Le codeur écrit réellement sur disque : ce qui doit être relu, audité et
    validé, c'est le diff, pas la prose de l'agent.

    Sur une branche reprise (second run du même ticket), `diff_depuis_base`
    étend le diff jusqu'au point de divergence de la branche : l'audit
    sécurité, le reviewer et le validateur voient tout le travail accumulé,
    pas seulement ce que le dernier tour n'a pas encore commité (ticket-208).
    Une seule fonction calcule le diff — `reviewed_code` est posé ici et les
    trois portes le lisent, sans recalcul.
    """
    if orch._git_workspace is None:
        return prose
    try:
        diff = await orch._git_workspace.diff_depuis_base()
    except GitWorkspaceError as exc:
        _logger.warning("diff_failed", extra={"error": str(exc)})
        _logger.info("diff_empty_fallback_to_prose", extra={"ticket_id": run.ticket_id})
        return prose
    if diff.strip():
        return diff
    _logger.info("diff_empty_fallback_to_prose", extra={"ticket_id": run.ticket_id})
    return prose


def _capture_artifact_diff(orch: "Orchestrator", run: PipelineRun) -> None:
    """Compute and store the artifact diff since run start.

    Populates ``run.artifact_diff`` with the textual diff of memory/ and
    tickets/ since the snapshot taken by ``take_artifact_snapshot``.  No-op
    when no snapshot exists (no project path, or not yet taken).

    This diff is intentionally kept separate from ``run.reviewed_code`` (the
    git diff): it is passed to the reviewer and the validator but never
    committed, so it does not affect what ends up in the repository.
    """
    if orch._project_path is None or run.artifact_snapshot is None:
        return
    run.artifact_diff = diff_artifacts(run.artifact_snapshot, orch._project_path)


def _role_qui_produit(type_de_ticket: "TicketType") -> AgentRole:
    """Qui tient l'étape « quelqu'un produit le travail », selon le ticket.

    Un ticket `design` appelle une décision d'architecture, pas du code. Le
    reste du pipeline est inchangé : le même reviewer relit, le même commit
    conclut.
    """
    if type_de_ticket is TicketType.design:
        return AgentRole.architect
    return AgentRole.codeur


# ------------------------------------------------------------------
# Testeur
# ------------------------------------------------------------------


async def run_tests(orch: "Orchestrator", run: PipelineRun) -> bool:
    """Lance la suite de tests du projet. Rend `False` si elle est rouge.

    Le résultat n'était qu'ajouté au contexte du reviewer : un ticket dont les
    tests cassent pouvait donc être approuvé par un reviewer qui n'avait pas
    regardé la ligne rouge. Le rendre ici permet à l'orchestrateur de renvoyer
    au codeur sans passer par la revue (ticket-098).

    Rend `True` quand il n'y a pas de testeur, ou pas de commande détectée :
    l'absence de test n'est pas un échec de test.
    """
    if not (orch._test_runner and orch._project_path):
        return True

    from tessera.services.test_runner import TestCommandNotFound

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
        return bool(result.passed)
    except TestCommandNotFound:
        orch._log(f"[{run.ticket_id}] testeur: commande non détectée, ignoré")
    except Exception as exc:
        # Le lanceur lui-même a échoué : on ne transforme pas sa panne en
        # échec du ticket, sinon une commande mal configurée bloquerait tout.
        _logger.warning("test_runner_failed", extra={"error": str(exc)})
    return True


# ------------------------------------------------------------------
# Sécurité
# ------------------------------------------------------------------


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
    try:
        audit = await orch._security_auditor.audit(
            code_diff=run.reviewed_code, project_path=orch._project_path
        )
    except Exception as exc:
        _logger.warning("security_auditor_failed", extra={"error": str(exc)})
        reason = f"Audit sécurité en panne : {exc}"
        audit = SecurityAuditResult(
            issues=[], verdict="BLOCK", summary=reason, reason=reason
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
        + run.artifact_diff
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
            data={
                "content": reviewer_result.content,
                "cost_usd": reviewer_result.cost_usd,
                "duration_ms": reviewer_result.duration_ms,
            },
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
    await emit(run, EventType.VALIDATION_STARTED)
    try:
        validation = await orch._validator.validate(
            criteria=_extract_criteria(run.ticket.body),
            code_produced=run.reviewed_code + run.artifact_diff,
            test_result=run.test_result,
        )
    except Exception as exc:
        # Échoue fermé, comme l'audit : une validation qui n'a pas eu lieu
        # n'approuve rien (ticket-122).
        _logger.warning("validator_failed", extra={"error": str(exc)})
        return False, f"Validation en panne : {exc}"

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

