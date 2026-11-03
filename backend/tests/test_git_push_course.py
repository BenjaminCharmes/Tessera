"""A push lost to a race on the same branch is recovered, never forced (ticket-539)."""
import asyncio
from pathlib import Path

import pytest

from tessera.services.git_workspace import GitCommandError, GitWorkspaceService


async def _git(cwd: Path, *args: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "git", *args, cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    assert proc.returncode == 0, err.decode()
    return out.decode()


class _ServiceCourse(GitWorkspaceService):
    """Refuses the first push the way GitHub does when two pushes race."""

    pushes: int = 0

    async def _run(self, *args: str) -> str:
        if args and args[0] == "push":
            self.pushes += 1
            if self.pushes == 1:
                raise GitCommandError(
                    command=["git", *args],
                    returncode=1,
                    stderr="! [remote rejected] b -> b (cannot lock ref: reference already exists)",
                )
        return await super()._run(*args)


@pytest.fixture
async def depot(tmp_path: Path) -> tuple[Path, Path, str]:
    """A project on a ticket branch with one commit, and an empty bare remote."""
    remote = tmp_path / "remote.git"
    remote.mkdir()
    await _git(remote, "init", "--bare", "-q")
    project = tmp_path / "projet"
    project.mkdir()
    await _git(project, "init", "-q")
    await _git(project, "config", "user.email", "t@t.local")
    await _git(project, "config", "user.name", "t")
    (project / "main.py").write_text("x = 1\n", encoding="utf-8")
    await _git(project, "add", "main.py")
    await _git(project, "commit", "-q", "-m", "initial")
    await _git(project, "remote", "add", "origin", str(remote))
    branch = await GitWorkspaceService(project).create_branch("ticket-539", "course")
    (project / "a.py").write_text("a = 1\n", encoding="utf-8")
    await GitWorkspaceService(project).commit_all("feat: a")
    return project, remote, branch


async def test_remote_already_at_head_counts_as_pushed(
    depot: tuple[Path, Path, str],
) -> None:
    project, remote, branch = depot
    await GitWorkspaceService(project).push_branch(branch)
    service = _ServiceCourse(project)

    await service.push_branch(branch)

    assert service.pushes == 1
    assert (await _git(remote, "rev-parse", branch)).strip() == (
        await _git(project, "rev-parse", "HEAD")
    ).strip()


async def test_remote_behind_head_is_pushed_again_without_force(
    depot: tuple[Path, Path, str],
) -> None:
    project, remote, branch = depot
    await GitWorkspaceService(project).push_branch(branch)
    (project / "b.py").write_text("b = 2\n", encoding="utf-8")
    await GitWorkspaceService(project).commit_all("chore: bookkeeping")
    service = _ServiceCourse(project)

    await service.push_branch(branch)

    assert service.pushes == 2
    assert (await _git(remote, "rev-parse", branch)).strip() == (
        await _git(project, "rev-parse", "HEAD")
    ).strip()


async def test_diverged_remote_keeps_the_refusal(
    depot: tuple[Path, Path, str],
) -> None:
    project, remote, branch = depot
    await GitWorkspaceService(project).push_branch(branch)
    pousse = (await _git(remote, "rev-parse", branch)).strip()
    await _git(project, "reset", "-q", "--hard", "HEAD~1")
    (project / "c.py").write_text("c = 3\n", encoding="utf-8")
    await GitWorkspaceService(project).commit_all("feat: autre")
    service = _ServiceCourse(project)

    with pytest.raises(GitCommandError):
        await service.push_branch(branch)

    assert service.pushes == 1
    assert (await _git(remote, "rev-parse", branch)).strip() == pousse


async def test_branch_absent_from_remote_keeps_the_refusal(
    depot: tuple[Path, Path, str],
) -> None:
    project, remote, branch = depot
    service = _ServiceCourse(project)

    with pytest.raises(GitCommandError):
        await service.push_branch(branch)

    assert service.pushes == 1
    assert branch not in await _git(remote, "branch", "--list")
