"""A run inside its own worktree: opening it, and removing it at the end — ticket-519.

ADR-056. A project that declares `worktree` never has its checkout written by a
run. The worktree is created under the run lock, before the tree is judged
clean, and removed once the delivery's first phase is over. Nothing here forces
anything: a worktree that holds unsaved work stays, and the run says where.
"""
from pathlib import Path
from typing import TYPE_CHECKING

from tessera.config import settings
from tessera.services.git_workspace import GitWorkspaceError, _branch_name
from tessera.services.pipeline_events import (
    EventCallback,
    EventType,
    OrchestratorEvent,
    PipelineResult,
)
from tessera.services.pipeline_run import PipelineRun, emit, set_status
from tessera.services.politique_run import PolitiqueRun
from tessera.services.run_worktree import (
    LienPersistant,
    RunWorktree,
    TravailNonSauve,
    creer,
    supprimer,
)
from tessera.services.run_worktree_populate import peupler
from tessera.models.ticket import TicketStatus
from tessera.utils.logger import get_logger

if TYPE_CHECKING:
    from tessera.services.orchestrator import Orchestrator

_logger = get_logger(__name__)


class OrchestrateurRefuse(Exception):
    """The worktree could not be opened: the run is refused before anything is written."""

    def __init__(self, arret: str) -> None:
        super().__init__(arret)
        self.arret = arret


def base_du_projet(politique: PolitiqueRun) -> str:
    """The branch a run forks from and delivers to: the declared one, else the global default."""
    return politique.base_branch or settings.github_base_branch


async def ouvrir_worktree(
    project_path: Path,
    project_id: str,
    ticket_id: str,
    titre: str,
    politique: PolitiqueRun,
) -> tuple[RunWorktree, list[str]] | None:
    """Create and populate the run worktree; `None` when the project declares none.

    Returns the worktree and the `populate` paths the checkout does not hold.
    Raises `OrchestrateurRefuse` when the branch is already checked out in the
    checkout, the folder is taken, or an id is refused: nothing was written to
    the checkout, and the run ends `blocked` without a commit.
    """
    config = politique.worktree
    if config is None:
        return None
    try:
        wt = await creer(
            project_path, project_path, project_id, ticket_id,
            _branch_name(ticket_id, titre), base_du_projet(politique),
        )
    except GitWorkspaceError as exc:
        raise OrchestrateurRefuse(str(exc)) from exc
    return wt, await peupler(wt, project_path, config)


async def retirer_apres_echec(wt: RunWorktree, depot: Path) -> None:
    """Remove a worktree on an error path; what cannot be removed is logged, never raised."""
    try:
        await supprimer(wt, depot)
    except (GitWorkspaceError, OSError) as exc:
        _logger.warning("run_worktree_non_supprime", extra={"racine": str(wt.racine), "erreur": str(exc)})


async def retirer_en_fin_de_run(
    orch: "Orchestrator", resultat: PipelineResult
) -> PipelineResult:
    """Remove the worktree after the final commit and the delivery's first phase.

    `TravailNonSauve` or `LienPersistant` put the run `blocked`, naming the folder
    that stays. Any other failure (`OSError`, git) is logged and the result comes
    back unchanged: a delivered run stays delivered, and the leftover worktree is
    taken up at startup. A run without worktree comes back unchanged.
    """
    wt = orch._worktree
    if wt is None or orch._depot is None or orch._worktree_retire:
        return resultat
    orch._worktree_retire = True
    try:
        await supprimer(wt, orch._depot)
    except (TravailNonSauve, LienPersistant) as exc:
        _logger.warning("run_worktree_conserve", extra={"racine": str(wt.racine)})
        orch._log(f"[{resultat.ticket_id}] {exc}")
        return resultat.model_copy(
            update={"final_status": TicketStatus.blocked, "arret": str(exc)}
        )
    except (GitWorkspaceError, OSError) as exc:
        extra = {"racine": str(wt.racine), "erreur": str(exc)}
        _logger.warning("run_worktree_non_supprime", extra=extra)
    return resultat


async def adopter_la_branche(orch: "Orchestrator", run: PipelineRun) -> PipelineResult | None:
    """Stage replacing `create_branch` in a worktree: the branch is already checked out.

    Neither the base nor the checkout is read or moved. A git refusal blocks the
    run like `create_branch` does (ADR-037).
    """
    wt = orch._worktree
    assert wt is not None and orch._git_workspace is not None
    try:
        run.branch = await orch._git_workspace.adopter_worktree(
            wt.branche, orch._base_branch or settings.github_base_branch
        )
    except GitWorkspaceError as exc:
        await set_status(orch, run, TicketStatus.blocked)
        await emit(run, EventType.ERROR, reason=str(exc))
        return PipelineResult(
            ticket_id=run.ticket_id, final_status=TicketStatus.blocked,
            rounds=0, approved=False, arret=str(exc),
        )
    await emit(run, EventType.BRANCH_CREATED, branch=run.branch)
    orch._log(f"[{run.ticket_id}] branche {run.branch} (worktree {wt.racine})")
    for chemin in orch._chemins_absents:
        orch._log(f"[{run.ticket_id}] worktree: « {chemin} » absent du checkout, non peuplé")
    return None


class RunRefuse:
    """Stands in for the orchestrator of a run whose worktree could not be opened.

    Only `run_pipeline` is called (single mode): it says why, ends `blocked`, and
    writes nothing — no status, no log, no commit.
    """

    def __init__(self, arret: str) -> None:
        self._arret = arret

    async def run_pipeline(
        self,
        project_id: str,
        ticket_id: str,
        on_event: EventCallback,
        run_id: str | None = None,
        dialogue: object | None = None,
        envelope_run_id: str | None = None,
    ) -> PipelineResult:
        await on_event(
            OrchestratorEvent(
                type=EventType.ERROR, ticket_id=ticket_id, project_id=project_id,
                data={"reason": self._arret},
            )
        )
        return PipelineResult(
            ticket_id=ticket_id, final_status=TicketStatus.blocked,
            rounds=0, approved=False, arret=self._arret,
        )
