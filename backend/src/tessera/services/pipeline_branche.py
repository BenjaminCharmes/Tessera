"""Stage — the ticket's own branch (ticket-688, split from `pipeline_stages`).

Refuses a tree something outside Tessera modified, then switches to the
ticket's branch. The base is realigned on the remote first (ticket-285,
ticket-406) and the pending pipeline-log lines are set aside around the switch
(ticket-331). A stage that can end the run returns a `PipelineResult`;
returning `None` means "carry on".
"""
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from tessera.models.ticket import TicketStatus
from tessera.services import journal_en_attente, pipeline_fin_de_file as fin_de_file
from tessera.services.git_workspace import GitWorkspaceError, NotAGitRepository
from tessera.services.pipeline_events import EventType, PipelineResult
from tessera.services.pipeline_rangement import ranger_les_bloques_livres
from tessera.services.pipeline_run import PipelineRun, emit, set_status
from tessera.services.run_dans_worktree import adopter_la_branche
from tessera.services.run_worktree import RunWorktree
from tessera.utils.logger import get_logger

if TYPE_CHECKING:
    from tessera.services.orchestrator import Orchestrator

_logger = get_logger(__name__)


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

    fichiers: list[str] = []
    try:
        fichiers = await orch._git_workspace.dirty_files()
    except GitWorkspaceError:
        pass

    noms = ", ".join(fichiers)
    arret = (
        f"l'arbre contient des modifications hors pipeline : {noms}"
        if noms
        else "l'arbre contient des modifications hors pipeline"
    )

    _logger.warning(
        "dirty_working_tree_refused",
        extra={"ticket_id": run.ticket_id, "fichiers": fichiers},
    )
    await set_status(orch, run, TicketStatus.blocked)
    await emit(
        run, EventType.ERROR,
        reason="dirty_working_tree",
        fichiers=fichiers,
        arret=arret,
    )
    return PipelineResult(
        ticket_id=run.ticket_id,
        final_status=TicketStatus.blocked,
        rounds=0,
        approved=False,
    )


async def create_branch(
    orch: "Orchestrator", run: PipelineRun
) -> Optional[PipelineResult]:
    """Switch to the ticket's own branch; degrade without one if git is absent.

    Aligns the base ref with the remote before forking (ticket-285).
    Returns a blocked ``PipelineResult`` when the local base has diverged
    from the remote and the run cannot safely start.

    Commits any pending pipeline bookkeeping (pipeline-log, ticket files)
    before switching branches: an interrupted delivery may have left them
    modified in the working tree, causing ``git checkout`` to refuse the
    switch when the base has a different version of those files (ticket-314).
    Only Tessera's own bookkeeping paths are staged — code files are not
    touched.  ``ensure_clean_tree`` still blocks on code modifications before
    this stage is reached.

    Pending pipeline-log lines are the exception: they are set aside before
    that commit and written back into the new branch's log, so that lines
    logged after a delivery's push reach the base with the next run instead
    of being stranded on the delivered branch (ticket-331).
    """
    if orch._git_workspace is None:
        return None
    # Dans un worktree de run (ADR-056) la branche est déjà extraite : rien à
    # basculer, rien à réaligner. isinstance : un double d'orchestrateur n'en a pas.
    if isinstance(getattr(orch, "_worktree", None), RunWorktree):
        return await adopter_la_branche(orch, run)

    racine = orch._project_path
    lignes = await journal_en_attente.mettre_de_cote(racine) if racine else []
    try:
        return await _basculer(orch, run, racine, lignes)
    finally:
        # Réécrites même si la branche n'a pas pu être créée : aucune ligne
        # ne se perd. Sans effet si `_basculer` l'a déjà fait.
        _reecrire_journal(racine, lignes)


def _reecrire_journal(racine: Optional[Path], lignes: list[str]) -> None:
    if racine is None:
        return
    try:
        journal_en_attente.reecrire(racine, lignes)
    except OSError as exc:
        _logger.warning("pending_log_rewrite_failed", extra={"error": str(exc)})


async def _realigner_base_au_depart(orch: "Orchestrator") -> Optional[str]:
    """Fast-forward the local base onto the remote before forking (ticket-406).

    The last ticket of a queue is merged by the CIWatcher after the run is
    over, so nobody realigns the base behind it: the next run would fork from
    a base that lags the remote. A tree left on the previous ticket's branch is
    first put back on the base (ticket-457): the pending log lines were already
    set aside by the caller, so the checkout is not in their way. Does nothing
    unless a git workspace and a base branch are known. Returns the refusal
    reason, or ``None`` when the base was realigned or nothing was attempted —
    a refusal (checkout included) never stops the run.
    """
    # getattr : les doubles d'orchestrateur des tests d'étape n'ont pas de base.
    base: Optional[str] = getattr(orch, "_base_branch", None)
    if orch._git_workspace is None or base is None:
        return None
    try:
        if not await fin_de_file.sur_la_base(orch):
            await orch._git_workspace.retourner_sur_base(base)
        return await orch._git_workspace.sync_base_depuis_distant(base)
    except GitWorkspaceError as exc:
        _logger.warning("realignement_debut_de_run_echoue", extra={"error": str(exc)})
        return str(exc)


async def _depart_sur_la_base(orch: "Orchestrator") -> bool:
    """True when the tree is on the base branch at the point of forking.

    Bookkeeping must not be committed there: a local commit would make the
    base diverge from the remote (no direct commit on develop or main).
    """
    if orch._git_workspace is None or getattr(orch, "_base_branch", None) is None:
        return False
    try:
        return await fin_de_file.sur_la_base(orch)
    except GitWorkspaceError:
        return False


async def _basculer(
    orch: "Orchestrator",
    run: PipelineRun,
    racine: Optional[Path],
    lignes: list[str],
) -> Optional[PipelineResult]:
    assert orch._git_workspace is not None

    # Avant tout commit de tenue de livres : le journal est déjà mis de côté,
    # l'arbre est donc propre pour l'avance rapide de la base (ticket-406).
    raison_base = await _realigner_base_au_depart(orch)

    # Les tickets bloqués puis livrés à la main passent en `done` sur la base
    # réalignée, avant le commit de tenue de livres qui les emporte (ticket-482).
    lignes_rangement = await ranger_les_bloques_livres(orch, run.ticket_id)

    # Commit pending bookkeeping before the branch switch.  Failures here
    # are logged but not fatal: the following branch creation attempt may
    # still succeed, and a missing bookkeeping commit is better than a
    # blocked pipeline when git is not fully configured.
    # Pas sur la base : un commit local la ferait diverger du distant. Les
    # modifications de `tickets/` suivent alors la branche du ticket (ticket-457).
    try:
        if not await _depart_sur_la_base(orch):
            await orch._git_workspace.commit_bookkeeping()
    except GitWorkspaceError as exc:
        _logger.warning("bookkeeping_before_branch_failed", extra={"error": str(exc)})

    try:
        # Sync base_branch with remote before forking the ticket branch (ticket-285).
        # A diverged local base blocks the run immediately rather than producing
        # a PR that GitHub will immediately reject.
        # Un ticket qui dépend d'un autre ne part jamais d'une base locale
        # faute de lire le distant : elle peut précéder le merge attendu
        # (ticket-340).
        raison_blocage = await orch._git_workspace.initialiser_base_ref(
            exiger_distant=bool(run.ticket.depends_on)
        )
        if raison_blocage is not None:
            _logger.warning("base_divergee_blocage", extra={"raison": raison_blocage})
            await set_status(orch, run, TicketStatus.blocked)
            await emit(run, EventType.ERROR, reason=raison_blocage)
            return PipelineResult(
                ticket_id=run.ticket_id,
                final_status=TicketStatus.blocked,
                rounds=0,
                approved=False,
                arret=raison_blocage,
            )
        run.branch = await orch._git_workspace.create_branch(
            run.ticket_id, run.ticket.title
        )
        # Avant la ligne « branche » : le journal garde son ordre.
        _reecrire_journal(racine, lignes)
        await emit(run, EventType.BRANCH_CREATED, branch=run.branch)
        orch._log(f"[{run.ticket_id}] branche {run.branch}")
        # Journalisé ici et non plus tôt : une ligne écrite avant le commit de
        # tenue de livres partirait en commit sur la base locale.
        if raison_base is not None:
            orch._log(f"[{run.ticket_id}] base non réalignée — {raison_base}")
        for ligne in lignes_rangement:
            orch._log(ligne)
    except NotAGitRepository:
        # Un projet sans dépôt git reste utilisable : on continue sans
        # garde-fou de branche plutôt que d'interrompre le pipeline.
        _logger.warning("branch_creation_no_repo", extra={"ticket_id": run.ticket_id})
    except GitWorkspaceError as exc:
        # Any other git error on a real repository: block the run (ADR-037,
        # ticket-314).  Running a ticket on the wrong branch — or without a
        # branch at all — lets subsequent commits land on whatever ref was
        # checked out, mixing unrelated work across tickets.
        arret = str(exc)
        _logger.warning("branch_creation_failed", extra={"error": arret})
        await set_status(orch, run, TicketStatus.blocked)
        await emit(run, EventType.ERROR, reason=arret)
        return PipelineResult(
            ticket_id=run.ticket_id,
            final_status=TicketStatus.blocked,
            rounds=0,
            approved=False,
            arret=arret,
        )
    return None
