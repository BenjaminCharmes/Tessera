"""What a run declares for its tests and its worktree setup, resolved for the run."""

from pathlib import Path

from fastapi import HTTPException

from tessera.services.gardes.politique_run import PolitiqueRun
from tessera.services.pipeline.preparation_worktree import Preparation, preparation_du_run
from tessera.services.verification.commande_effective import PlaceholderInconnu, commande_effective, environnement_effectif
from tessera.services.worktrees.run_worktree import RunWorktree


def delai_du_setup(politique: PolitiqueRun, test_timeout_s: int | None) -> int | None:
    """The setup timeout: `worktree.setup_timeout_s` when declared, else the tests' one."""
    if politique.worktree is not None and politique.worktree.setup_timeout_s is not None:
        return politique.worktree.setup_timeout_s
    return test_timeout_s


def preparation_du_run_declaree(
    politique: PolitiqueRun,
    wt: RunWorktree | None,
    project_path: Path,
    env: dict[str, str] | None,
    timeout: int | None,
) -> Preparation | None:
    """The declared `worktree.setup` of the run; an unknown placeholder refuses it (422)."""
    try:
        return preparation_du_run(
            politique, wt.racine if wt is not None else None, project_path, env,
            delai_du_setup(politique, timeout),
        )
    except PlaceholderInconnu as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def tests_du_run(
    politique: PolitiqueRun, wt: RunWorktree | None, project_path: Path
) -> tuple[str | None, dict[str, str] | None]:
    """The test command and environment of the run: the declared ones, or the worktree's.

    Un placeholder inconnu refuse le run (422) : lancer un `{faute}` littéral
    ne dirait rien de juste.
    """
    if wt is None or politique.worktree is None:
        return politique.test_command, None
    try:
        return (
            commande_effective(politique, wt.racine, project_path),
            environnement_effectif(politique.worktree, wt.racine, project_path),
        )
    except PlaceholderInconnu as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
