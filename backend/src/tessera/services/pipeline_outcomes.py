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


async def finish_timeout_expired(
    orch: "Orchestrator", run: PipelineRun
) -> PipelineResult:
    """Block the run when the test suite times out twice in a row (ticket-349).

    Deux expirations consécutives signifient que la machine ou la suite est trop
    lente pour le délai configuré, et non que le code est en cause.  Bloquer
    ici évite de consommer un tour de codeur pour rien.
    """
    raison = "testeur: délai dépassé deux fois"
    await set_status(orch, run, TicketStatus.blocked)
    await emit(run, EventType.ERROR, reason="test_timeout_expired", detail=raison)
    orch._log(f"[{run.ticket_id}] BLOCKED — {raison}")
    commit_sha, arret = await commit_ou_bloquer(
        orch, run, _unapproved_commit_message(run.ticket_id, raison)
    )
    await emit(
        run,
        EventType.PIPELINE_DONE,
        approved=False,
        rounds=run.round_num,
        reason="test_timeout_expired",
        branch=run.branch,
    )
    return PipelineResult(
        ticket_id=run.ticket_id,
        final_status=TicketStatus.blocked,
        rounds=run.round_num,
        approved=False,
        branch=run.branch,
        commit_sha=commit_sha,
        arret=arret or raison,
    )


async def finish_security_block(
    orch: "Orchestrator", run: PipelineRun, summary: str
) -> PipelineResult:
    await set_status(orch, run, TicketStatus.blocked)
    commit_sha, arret = await commit_ou_bloquer(
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
        branch=run.branch,
    )
    return PipelineResult(
        ticket_id=run.ticket_id,
        final_status=TicketStatus.blocked,
        rounds=run.round_num,
        approved=False,
        branch=run.branch,
        commit_sha=commit_sha,
        arret=arret,
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


async def commit_ou_bloquer(
    orch: "Orchestrator", run: PipelineRun, message: str
) -> tuple[str | None, str | None]:
    """Commit the work; on failure, return the cause instead of raising.

    Le point de sortie unique de tous les `finish_*` (ticket-121). Avant,
    seul `finish_approved` attrapait `CommitFailed` : sur un blocage
    sécurité, un arrêt ou un épuisement des tours, l'exception remontait à
    `_run_pipeline`, qui appelait `finish_interrupted`, qui rappelait
    `commit_work`, qui relevait — 500 FastAPI, arbre sale, run jamais clos.
    Un commit raté est une sortie du run comme une autre : il se nomme dans
    `arret`, il ne se propage pas.
    """
    try:
        return await commit_work(orch, run, message), None
    except CommitFailed as exc:
        return None, f"commit_failed: {_single_line(str(exc))[:200]}"


async def finish_approved(orch: "Orchestrator", run: PipelineRun) -> PipelineResult:
    """Mark the ticket done, commit under its own type, advance the base ref.

    L'approbation n'est prononcée qu'une fois le commit passé : un run qui a
    produit du travail mais n'a pas su l'enregistrer n'a pas fini son travail,
    quoi qu'en pense le reviewer.
    """
    orch._log(f"[{run.ticket_id}] APPROVED après {run.round_num} tour(s)")

    # Le ticket change de statut **avant** le commit, comme sur toutes les
    # autres sorties. `finish_approved` était le seul à faire l'inverse : le
    # déplacement du fichier de `in-review/` vers `done/` arrivait après le
    # dernier commit et restait dans l'arbre. ADR-018 veut un arbre propre à
    # la sortie, et ici ce n'est pas le ticket suivant qui trinquait mais la
    # livraison du ticket courant, immédiate : `git rebase` refuse de démarrer
    # sur des modifications non commitées (ticket-159).
    await set_status(orch, run, TicketStatus.done)

    # Ce message est écrit dans le dépôt *de l'utilisateur* : il suit donc la
    # convention de ce dépôt — Conventional Commits — avec le type du ticket
    # plutôt qu'un "feat:" codé en dur, qui mal-étiquetait les fix/chore/docs.
    commit_sha, arret = await commit_ou_bloquer(
        orch,
        run,
        f"{run.ticket.type.value}: {run.ticket_id} — {_single_line(run.ticket.title)}",
    )
    if arret is not None:
        # « Rien à committer » (commit_sha None) reste un succès : le travail
        # existait déjà. Un commit *raté* est autre chose, et le ticket ne peut
        # pas passer `done` dessus.
        await set_status(orch, run, TicketStatus.blocked)
        await emit(
            run,
            EventType.PIPELINE_DONE,
            approved=False,
            rounds=run.round_num,
            branch=run.branch,
        )
        return PipelineResult(
            ticket_id=run.ticket_id,
            final_status=TicketStatus.blocked,
            rounds=run.round_num,
            approved=False,
            branch=run.branch,
            arret=arret,
        )

    # `branch` sur chaque sortie : l'UI reconstruit son résultat depuis cet
    # événement, et sans la branche elle proposait de « lancer d'abord le
    # pipeline » après un run approuvé (ticket-123).
    await emit(
        run, EventType.PIPELINE_DONE, approved=True, rounds=run.round_num, branch=run.branch
    )

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
    orch._log(f"[{run.ticket_id}] ARRÊTÉ par l'utilisateur au tour {run.round_num}")
    commit_sha, arret = await commit_ou_bloquer(
        orch, run, _unapproved_commit_message(run.ticket_id, "arrêt demandé")
    )
    await emit(
        run, EventType.PIPELINE_DONE, approved=False, rounds=run.round_num, branch=run.branch
    )
    return PipelineResult(
        ticket_id=run.ticket_id,
        final_status=TicketStatus.blocked,
        rounds=run.round_num,
        approved=False,
        branch=run.branch,
        commit_sha=commit_sha,
        arret=arret,
    )


async def finish_rounds_exhausted(
    orch: "Orchestrator", run: PipelineRun
) -> PipelineResult:
    """Block the ticket after the last round, committing the work all the same."""
    await set_status(orch, run, TicketStatus.blocked)
    orch._log(
        f"[{run.ticket_id}] BLOCKED après {orch._max_review_rounds} tour(s) sans approbation"
    )
    commit_sha, arret = await commit_ou_bloquer(
        orch,
        run,
        _unapproved_commit_message(
            run.ticket_id,
            "changes requested — rounds exhausted after "
            f"{orch._max_review_rounds} round(s)",
        ),
    )
    await emit(
        run,
        EventType.PIPELINE_DONE,
        approved=False,
        rounds=orch._max_review_rounds,
        branch=run.branch,
    )
    return PipelineResult(
        ticket_id=run.ticket_id,
        final_status=TicketStatus.blocked,
        rounds=orch._max_review_rounds,
        approved=False,
        branch=run.branch,
        commit_sha=commit_sha,
        arret=arret,
    )


async def finish_budget_exhausted(
    orch: "Orchestrator", run: PipelineRun
) -> PipelineResult:
    """Block the ticket when the run's spending cap is reached between two
    rounds, committing the work all the same (ticket-191).

    Une frontière de tour a la propriété qu'ADR-020 exige d'une frontière de
    ticket : le codeur a fini d'écrire, et rien n'est à mi-chemin.
    """
    await set_status(orch, run, TicketStatus.blocked)
    raison = (
        f"run budget exhausted: {orch.spent_usd:.2f} USD spent "
        f"of {orch._run_max_budget_usd:.2f} allowed"
    )
    orch._log(f"[{run.ticket_id}] BLOCKED après le tour {run.round_num} — {raison}")
    commit_sha, arret = await commit_ou_bloquer(
        orch, run, _unapproved_commit_message(run.ticket_id, raison)
    )
    await emit(
        run,
        EventType.PIPELINE_DONE,
        approved=False,
        rounds=run.round_num,
        reason="run_budget_exhausted",
        branch=run.branch,
    )
    return PipelineResult(
        ticket_id=run.ticket_id,
        final_status=TicketStatus.blocked,
        rounds=run.round_num,
        approved=False,
        branch=run.branch,
        commit_sha=commit_sha,
        arret=arret or raison,
    )


async def finish_session_limit(
    orch: "Orchestrator", run: PipelineRun, cause: BaseException, reset_time: str | None
) -> PipelineResult:
    """Termine un run interrompu par la limite de session de l'abonnement.

    Contrairement aux autres sorties en erreur, le ticket repasse en `todo`
    pour être relancé dès la reprise de la session — un ticket `blocked`
    resterait en attente d'une intervention manuelle qui n'est pas nécessaire
    ici : la limite est temporaire, pas une vraie panne.

    Le travail est quand même commité, comme sur toutes les autres sorties
    (ADR-018) : l'arbre doit rester propre pour le ticket suivant, même si
    la file s'arrête ici.
    """
    reset_info = f" (reprise : {reset_time})" if reset_time else ""
    raison = f"session_limit{reset_info}"
    # Le log **avant** le commit : la ligne doit figurer dans le commit final
    # (même règle que finish_interrupted, corrigée dans ticket-219).
    orch._log(
        f"[{run.ticket_id}] INTERROMPU par limite de session{reset_info}"
    )
    await set_status(orch, run, TicketStatus.todo)
    await emit(run, EventType.ERROR, reason="session_limit", reset_time=reset_time or "")
    commit_sha, echec_commit = await commit_ou_bloquer(
        orch, run, _unapproved_commit_message(run.ticket_id, f"session limit{reset_info}")
    )
    if echec_commit is not None:
        raison = f"{echec_commit} (après {raison})"
    await emit(
        run,
        EventType.PIPELINE_DONE,
        approved=False,
        rounds=run.round_num,
        reason="session_limit",
        branch=run.branch,
    )
    return PipelineResult(
        ticket_id=run.ticket_id,
        final_status=TicketStatus.todo,
        rounds=run.round_num,
        approved=False,
        branch=run.branch,
        commit_sha=commit_sha,
        arret=raison,
    )


async def finish_interrupted(
    orch: "Orchestrator", run: PipelineRun, cause: BaseException
) -> PipelineResult:
    """Termine un run qu'une panne de production a interrompu, sans perdre son travail.

    Le premier run réel du ticket-101 s'est arrêté sur un plafond du SDK
    (`Reached maximum budget ($1)`) atteint au milieu du tour du codeur.
    L'exception est remontée jusqu'à FastAPI : aucun commit, arbre laissé
    sale, et un run resté `finished_at` nul en base.

    Rendre un résultat plutôt que propager règle les trois d'un coup — le
    travail est commité, l'arbre redevient propre pour le ticket suivant
    (ADR-018), et l'appelant clôt l'enregistrement du run comme sur n'importe
    quelle autre sortie.

    C'est le raisonnement d'ADR-030, appliqué à la production : une panne
    d'infrastructure ne doit pas faire perdre ce qui a déjà été écrit.
    """
    await set_status(orch, run, TicketStatus.blocked)
    raison = f"{type(cause).__name__}: {_single_line(str(cause))[:120]}"
    await emit(run, EventType.ERROR, reason="interrupted", detail=raison)
    orch._log(f"[{run.ticket_id}] INTERROMPU au tour {run.round_num} — {raison}")
    commit_sha, echec_commit = await commit_ou_bloquer(
        orch, run, _unapproved_commit_message(run.ticket_id, raison)
    )
    # Dernier filet de `_run_pipeline` : si le commit échoue ici aussi, la
    # panne d'origine ne doit pas disparaître derrière l'échec du commit.
    if echec_commit is not None:
        raison = f"{echec_commit} (après {raison})"
    await emit(
        run,
        EventType.PIPELINE_DONE,
        approved=False,
        rounds=run.round_num,
        reason="interrupted",
        branch=run.branch,
    )
    return PipelineResult(
        ticket_id=run.ticket_id,
        final_status=TicketStatus.blocked,
        rounds=run.round_num,
        approved=False,
        branch=run.branch,
        commit_sha=commit_sha,
        arret=raison,
    )
