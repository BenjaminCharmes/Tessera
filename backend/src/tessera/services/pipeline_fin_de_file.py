"""Merge wait, base realignment and cleanup — ticket-686.

What the orchestrator does after a delivery or at the end of a queue. The
functions take the orchestrator as their first argument, like the other
`pipeline_*` modules; `Orchestrator` is only imported for typing.
"""
import asyncio
from typing import TYPE_CHECKING

from tessera.services.livraison_evenements import attente_annoncee
from tessera.services.pipeline_events import EventCallback
from tessera.utils.logger import get_logger

if TYPE_CHECKING:
    from tessera.services.livraison import Livraison
    from tessera.services.orchestrator import Orchestrator

_logger = get_logger(__name__)

# Nombre de fichiers non suivis nommés dans une ligne de journal (ticket-480).
_MAX_FICHIERS_SIGNALES = 10


async def attendre_merge_et_syncer(
    orch: "Orchestrator",
    project_id: str,
    ticket_id: str,
    pr_number: int | None = None,
    on_event: EventCallback | None = None,
) -> bool:
    """Wait for the merge, then realign the local base; True only when merged.

    Called before every next ticket under merge_without_ci (ticket-382). A timeout
    is logged and counts as not merged: only the dependents skip (ticket-666).
    """
    assert orch._ci_watcher is not None
    try:
        async with attente_annoncee(on_event, ticket_id, pr_number):
            merged = await asyncio.wait_for(
                orch._ci_watcher.attendre_merge(
                    project_id, ticket_id, pr_number=pr_number, etat_pr=orch._etat_pr
                ),
                timeout=orch._attente_merge_max_s,
            )
    except asyncio.TimeoutError:
        orch._log(
            f"[{project_id}] {ticket_id} : délai d'attente du merge dépassé"
            f" ({orch._attente_merge_max_s:.0f}s) — ticket suivant sans réalignement"
        )
        return False
    if merged:
        await realigner_base(orch, project_id, ticket_id)
    return bool(merged)


async def realigner_base(
    orch: "Orchestrator", project_id: str, ticket_id: str
) -> None:
    """Fast-forward the local base onto the remote after ``ticket_id`` merged.

    Shared by the merge_without_ci wait (ticket-382) and the dependency
    wait (ticket-403). A refused sync is logged, never raised.
    """
    if orch._git_workspace is None or orch._base_branch is None:
        return
    raison = await orch._git_workspace.sync_base_depuis_distant(orch._base_branch)
    if raison is not None:
        orch._log(
            f"[{project_id}] {ticket_id} : réalignement de la base ignoré — {raison}"
        )
    else:
        orch._log(f"[{project_id}] {ticket_id} : base réalignée sur {orch._base_branch}")


async def finaliser_livraison(
    orch: "Orchestrator", livraison: "Livraison"
) -> None:
    """Commit delivery log lines and return to the base branch (ticket-378, ticket-390).

    Called after any delivery attempt, whether or not a PR was opened. The
    log lines written just before this call are in ``pipeline-log.md`` but
    not yet committed; ``commit_bookkeeping`` picks them up so they appear
    in the last commit of the ticket branch.  Checking out the base branch
    then leaves the working tree clean, matching ADR-018.

    Errors are logged and swallowed: a failure here must not undo an
    already-opened PR.
    """
    if orch._git_workspace is None:
        return
    try:
        if not await sur_la_base(orch):
            await orch._git_workspace.commit_bookkeeping()
    except Exception as exc:  # noqa: BLE001
        _logger.warning("livraison_bookkeeping_failed", extra={"error": str(exc)})
    if orch._base_branch is None:
        return
    try:
        await orch._git_workspace.retourner_sur_base(orch._base_branch)
    except Exception as exc:  # noqa: BLE001
        _logger.warning("livraison_checkout_base_failed", extra={"error": str(exc)})


async def signaler_fichiers_non_suivis(
    orch: "Orchestrator", etiquette: str
) -> None:
    """Log the untracked files a run left in the tree; delete nothing (ticket-480).

    Un client généré (Prisma, par exemple) reste non suivi après un run
    bloqué : la ligne de journal dit lesquels, pour qu'on décide de les
    ignorer. Une erreur ici est journalisée et avalée.
    """
    if orch._git_workspace is None:
        return
    # getattr : les doubles d'espace de travail des tests n'ont pas cette méthode.
    lister = getattr(orch._git_workspace, "fichiers_non_suivis_laisses", None)
    if lister is None:
        return
    try:
        fichiers = list(await lister())
    except Exception as exc:  # noqa: BLE001
        _logger.warning("fichiers_non_suivis_illisibles", extra={"error": str(exc)})
        return
    if not fichiers:
        return
    vus = ", ".join(str(f) for f in fichiers[:_MAX_FICHIERS_SIGNALES])
    if len(fichiers) > _MAX_FICHIERS_SIGNALES:
        vus += f" et {len(fichiers) - _MAX_FICHIERS_SIGNALES} autres"
    orch._log(
        f"[{etiquette}] fichiers non suivis laissés par le run : {vus} "
        "(à ignorer dans .gitignore ?)"
    )


async def nettoyer_apres_file(orch: "Orchestrator") -> None:
    """Commit remaining log lines and return to the base branch after a queue.

    The 'file interrompue' lines written after the last ticket's own
    bookkeeping commit modify pipeline-log.md but are not yet committed.
    This function ensures nothing stays uncommitted, and the working tree is
    left on the base branch regardless of how the queue ended (ticket-390).

    Errors are logged and swallowed: a cleanup failure must not mask the
    queue's own result.
    """
    if orch._git_workspace is None or orch._base_branch is None:
        return
    try:
        if not await sur_la_base(orch):
            await orch._git_workspace.commit_bookkeeping()
    except Exception as exc:  # noqa: BLE001
        _logger.warning("queue_bookkeeping_failed", extra={"error": str(exc)})
    try:
        await orch._git_workspace.retourner_sur_base(orch._base_branch)
    except Exception as exc:  # noqa: BLE001
        _logger.warning("queue_checkout_base_failed", extra={"error": str(exc)})


async def sur_la_base(orch: "Orchestrator") -> bool:
    """True when the working tree is already on the base branch.

    Bookkeeping is never committed there: a local commit on the base
    branch would diverge it from the remote (no direct commit on develop
    or main). The lines stay in the tree and ride with the next ticket's
    branch, as before ticket-390.
    """
    if orch._git_workspace is None or orch._base_branch is None:
        return False
    branche_courante = getattr(orch._git_workspace, "branche_courante", None)
    if branche_courante is None:
        return False
    return bool(await branche_courante() == orch._base_branch)
