"""A throwaway git worktree, to write into a repository without touching its tree — ticket-479.

The main working tree of a project may be occupied by a run (ADR-018: one
branch, one commit, a tree that is never left dirty). Anything that must reach
the repository meanwhile is written elsewhere: a detached worktree, created
from a ref and removed when the work is done, whatever happened in between.
"""
import asyncio
import shutil
import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from tessera.services.git_workspace import GitCommandError, _dossier_sans_hooks
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)


async def run_git(cwd: Path, *args: str) -> str:
    """Run git in `cwd` and return stdout; raise `GitCommandError` on failure.

    Repository hooks never run from here, for the reason given in
    `GitWorkspaceService._run`: they live under the project root.
    """
    command = [
        "git",
        "-c", f"core.hooksPath={_dossier_sans_hooks()}",
        "-c", "core.quotePath=false",
        "-c", "core.longpaths=true",
        *args,
    ]
    proc = await asyncio.create_subprocess_exec(
        *command,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise GitCommandError(
            command=command,
            returncode=proc.returncode or 0,
            stderr=stderr.decode("utf-8", errors="replace"),
        )
    return stdout.decode("utf-8", errors="replace")


async def _remove(repo: Path, root: Path, parent: Path) -> None:
    """Drop the worktree and its folder; never raise, never mask the caller's error."""
    try:
        await run_git(repo, "worktree", "remove", "--force", str(root))
    except GitCommandError as exc:
        _logger.warning("worktree_remove_failed", extra={"error": str(exc)})
    shutil.rmtree(parent, ignore_errors=True)
    try:
        # Efface l'enregistrement d'un worktree dont le dossier a disparu.
        await run_git(repo, "worktree", "prune")
    except GitCommandError as exc:
        _logger.warning("worktree_prune_failed", extra={"error": str(exc)})


@asynccontextmanager
async def detached_worktree(repo: Path, ref: str) -> AsyncIterator[Path]:
    """Yield the root of a temporary worktree of `repo`, detached at `ref`.

    `repo` is only the place git is asked from; its working tree is not read
    or written. The worktree is removed on exit, including when the body or
    the creation itself raised.
    """
    parent = Path(tempfile.mkdtemp(prefix="tessera-worktree-"))
    root = parent / "tree"
    try:
        await run_git(repo, "worktree", "add", "--detach", str(root), ref)
        yield root
    finally:
        await _remove(repo, root, parent)
