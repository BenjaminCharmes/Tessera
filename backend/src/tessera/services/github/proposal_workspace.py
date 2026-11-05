"""The git gestures `GitHubWorkflowService` needs, on a throwaway worktree — ticket-479.

The worktree is detached: it has no local branch, and the local base branch of
the project may lag behind the remote one. Everything is therefore expressed
against `origin/<base>` and `HEAD`, never against names that only exist in the
main working tree.
"""
from pathlib import Path

from tessera.services.git_workspace import GitWorkspaceService
from tessera.services.politique_run import PolitiqueRun
from tessera.services.temporary_worktree import run_git
from tessera.services.termes_interdits import CommitInfo


class ProposalWorkspace:
    """Git on the worktree of a proposal: push `HEAD`, read what it adds to the base."""

    def __init__(self, project_dir: Path, policy: PolitiqueRun) -> None:
        self._dir = project_dir
        self._git = GitWorkspaceService(project_dir, politique=policy)

    async def push_branch(self, branch_name: str) -> None:
        """Publish `HEAD` as `branch_name`. Never forced (ADR-022)."""
        await run_git(self._dir, "push", "origin", f"HEAD:refs/heads/{branch_name}")

    async def current_diff(self) -> str:
        return await self._git.current_diff()

    async def diff_de_branche(self, base: str, branch: str) -> str:
        """What `HEAD` adds to the remote `base`; `branch` is only a name here."""
        return await self._git.diff_de_branche(f"origin/{base}", "HEAD")

    async def commits_depuis_base(self, base: str, branch: str) -> list[CommitInfo]:
        return await self._git.commits_depuis_base(f"origin/{base}", "HEAD")
