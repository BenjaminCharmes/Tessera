"""How a pipeline run ends — ticket-046.

Split from `pipeline_stages.py`: the stages describe what the agents do, these
functions describe how a run terminates and what it leaves behind in git. They
are the part where a mistake writes something wrong into the user's repository,
so they are worth reading on their own.
"""
from typing import TYPE_CHECKING

from tessera.models.ticket import TicketStatus
from tessera.services.git_workspace import GitWorkspaceError
from tessera.services.pipeline_events import EventType, PipelineResult
from tessera.services.pipeline_run import PipelineRun, emit, set_status
from tessera.services.pipeline_text import _single_line, _unapproved_commit_message
from tessera.utils.logger import get_logger

if TYPE_CHECKING:
    from tessera.services.orchestrator import Orchestrator

_logger = get_logger(__name__)


class CommitFailed(Exception):
    """Le commit de fin de run a échoué — le run ne peut pas s'annoncer réussi."""


async def finish_security_block(
    orch: "Orchestrator", run: PipelineRun, summary: str
) -> PipelineResult:
    await set_status(orch, run, TicketStatus.blocked)
    commit_sha = await commit_work(
        orch,
        run,
        _unapproved_commit_message(
            run.ticket_id, f"security block: {_single_line(summary)[:80]}"
        ),
    )
    await emit(
        run,
        EventType.PIPELINE_DONE,
        approved=False,
        rounds=run.round_num,
        reason="security_block",
    )
    return PipelineResult(
        ticket_id=run.ticket_id,
        final_status=TicketStatus.blocked,
        rounds=run.round_num,
        approved=False,
        branch=run.branch,
        commit_sha=commit_sha,
    )




async def commit_work(
    orch: "Orchestrator", run: PipelineRun, message: str
) -> str | None:
    """Commit whatever the coder produced; emit COMMIT_CREATED.

    Gated on both `git_workspace` being configured and `branch` being set — a
    failed branch creation must never result in a commit onto whatever ref
    happened to be checked out. Applies on every exit path, approved or not:
    isolation-by-branch relies on each run leaving the tree clean for the next.
    """
    if orch._git_workspace is None or run.branch is None:
        return None
    try:
        commit_sha = await orch._git_workspace.commit_all(message)
    except GitWorkspaceError as exc:
        # Cet échec était un simple `warning` : il partait dans les logs du
        # serveur et le run annonçait quand même APPROVED. Le travail restait
        # alors dans l'arbre, le ticket suivant le trouvait sale et se
        # bloquait, et rien à l'écran ne reliait les deux (ticket-068).
        _logger.warning("commit_failed", extra={"error": str(exc)})
        await emit(run, EventType.ERROR, reason="commit_failed", message=str(exc))
        raise CommitFailed(str(exc)) from exc
    if commit_sha is not None:
        await emit(run, EventType.COMMIT_CREATED, sha=commit_sha, branch=run.branch)
    return commit_sha


async def finish_approved(orch: "Orchestrator", run: PipelineRun) -> PipelineResult:
    """Mark the ticket done, commit under its own type, advance the base ref.

    L'approbation n'est prononcée qu'une fois le commit passé : un run qui a
    produit du travail mais n'a pas su l'enregistrer n'a pas fini son travail,
    quoi qu'en pense le reviewer.
    """
    orch._log(f"[{run.ticket_id}] APPROVED après {run.round_num} tour(s)")

    # Ce message est écrit dans le dépôt *de l'utilisateur* : il suit donc la
    # convention de ce dépôt — Conventional Commits — avec le type du ticket
    # plutôt qu'un "feat:" codé en dur, qui mal-étiquetait les fix/chore/docs.
    try:
        commit_sha = await commit_work(
            orch, run, f"{run.ticket.type.value}: {run.ticket_id} — {run.ticket.title}"
        )
    except CommitFailed:
        # « Rien à committer » (commit_sha None) reste un succès : le travail
        # existait déjà. Un commit *raté* est autre chose, et le ticket ne peut
        # pas passer `done` dessus.
        await set_status(orch, run, TicketStatus.blocked)
        await emit(run, EventType.PIPELINE_DONE, approved=False, rounds=run.round_num)
        return PipelineResult(
            ticket_id=run.ticket_id,
            final_status=TicketStatus.blocked,
            rounds=run.round_num,
            approved=False,
            branch=run.branch,
        )

    await set_status(orch, run, TicketStatus.done)
    await emit(run, EventType.PIPELINE_DONE, approved=True, rounds=run.round_num)

    # Seul un ticket *approuvé* avance la ref de base. L'isolation par branche
    # garde le travail rejeté hors du ticket suivant ; elle ne doit pas aussi
    # cacher le travail approuvé aux tickets qui suivent, sinon chaque étape
    # d'un plan séquentiel tournerait sur une base périmée.
    if commit_sha is not None and orch._git_workspace is not None:
        try:
            await orch._git_workspace.advance_base_ref()
        except GitWorkspaceError as exc:
            _logger.warning("advance_base_ref_failed", extra={"error": str(exc)})

    return PipelineResult(
        ticket_id=run.ticket_id,
        final_status=TicketStatus.done,
        rounds=run.round_num,
        approved=True,
        branch=run.branch,
        commit_sha=commit_sha,
    )


async def finish_stopped(orch: "Orchestrator", run: PipelineRun) -> PipelineResult:
    """Termine un run que l'utilisateur a interrompu, en commitant son travail.

    Le travail est commité comme sur toute autre sortie : ADR-018 fait dépendre
    le ticket suivant d'un arbre propre, et un arrêt qui laisserait le travail
    en plan bloquerait la file — exactement la panne qu'on a corrigée ailleurs.

    Le ticket passe `blocked` et non `todo` : en mode autonome, un ticket
    laissé `todo` serait repris au tour suivant, et un arrêt demandé par
    l'utilisateur serait sans effet.
    """
    await set_status(orch, run, TicketStatus.blocked)
    await emit(run, EventType.ERROR, reason="stopped_by_user")
    commit_sha = await commit_work(
        orch, run, _unapproved_commit_message(run.ticket_id, "arrêt demandé")
    )
    await emit(run, EventType.PIPELINE_DONE, approved=False, rounds=run.round_num)
    orch._log(f"[{run.ticket_id}] ARRÊTÉ par l'utilisateur au tour {run.round_num}")
    return PipelineResult(
        ticket_id=run.ticket_id,
        final_status=TicketStatus.blocked,
        rounds=run.round_num,
        approved=False,
        branch=run.branch,
        commit_sha=commit_sha,
    )


async def finish_rounds_exhausted(
    orch: "Orchestrator", run: PipelineRun
) -> PipelineResult:
    """Block the ticket after the last round, committing the work all the same."""
    await set_status(orch, run, TicketStatus.blocked)
    commit_sha = await commit_work(
        orch,
        run,
        _unapproved_commit_message(
            run.ticket_id,
            "changes requested — rounds exhausted after "
            f"{orch._max_review_rounds} round(s)",
        ),
    )
    await emit(
        run, EventType.PIPELINE_DONE, approved=False, rounds=orch._max_review_rounds
    )
    orch._log(
        f"[{run.ticket_id}] BLOCKED après {orch._max_review_rounds} tour(s) sans approbation"
    )
    return PipelineResult(
        ticket_id=run.ticket_id,
        final_status=TicketStatus.blocked,
        rounds=orch._max_review_rounds,
        approved=False,
        branch=run.branch,
        commit_sha=commit_sha,
    )
