"""`remettre_sur` puts a rebased branch back on its earlier head — ticket-740."""

import asyncio
from pathlib import Path

import pytest

from tessera.services.git_workspace import GitCommandError, GitWorkspaceService


async def _git(cwd: Path, *args: str) -> str:
    """Run a git command in *cwd* and return stdout; raise on non-zero."""
    proc = await asyncio.create_subprocess_exec(
        "git", *args, cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    assert proc.returncode == 0, f"git {' '.join(args)}: {stderr.decode()}"
    return stdout.decode().strip()


@pytest.fixture
async def repo(tmp_path: Path) -> Path:
    """Repository with a branch that diverged from `main`."""
    root = tmp_path / "projet"
    root.mkdir()
    await _git(root, "init", "-q", "-b", "main")
    await _git(root, "config", "user.email", "test@tessera.local")
    await _git(root, "config", "user.name", "Tessera test")
    (root / "a.txt").write_text("a\n", encoding="utf-8")
    await _git(root, "add", "a.txt")
    await _git(root, "commit", "-q", "-m", "init")
    await _git(root, "checkout", "-q", "-b", "ticket-001-x")
    (root / "b.txt").write_text("b\n", encoding="utf-8")
    await _git(root, "add", "b.txt")
    await _git(root, "commit", "-q", "-m", "feat: b")
    await _git(root, "checkout", "-q", "main")
    (root / "c.txt").write_text("c\n", encoding="utf-8")
    await _git(root, "add", "c.txt")
    await _git(root, "commit", "-q", "-m", "chore: c")
    await _git(root, "checkout", "-q", "ticket-001-x")
    return root


async def test_remettre_sur_restores_the_head_a_rebase_moved(repo: Path) -> None:
    avant = await _git(repo, "rev-parse", "HEAD")
    service = GitWorkspaceService(repo)
    assert await service.rejouer_sur("main") == ()
    assert await _git(repo, "rev-parse", "HEAD") != avant

    await service.remettre_sur(avant)

    assert await _git(repo, "rev-parse", "HEAD") == avant
    assert await _git(repo, "branch", "--show-current") == "ticket-001-x"
    assert await _git(repo, "status", "--porcelain") == ""


async def test_remettre_sur_raises_when_the_branch_cannot_move(repo: Path) -> None:
    service = GitWorkspaceService(repo)

    with pytest.raises(GitCommandError):
        await service.remettre_sur("0" * 40)
