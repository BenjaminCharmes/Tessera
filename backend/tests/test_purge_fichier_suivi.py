"""A run's purge never untracks a file already in HEAD — ticket-446.

`_purger_stage_ignoré` only removes from the index the paths that an exclusion
rule covers *and* that the base commit does not carry.
"""

import asyncio
from pathlib import Path

import pytest

from tessera.services.git_workspace import GitWorkspaceService


async def _git(cwd: Path, *args: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    assert proc.returncode == 0, err.decode()
    return out.decode()


@pytest.fixture
async def repo(tmp_path: Path) -> Path:
    root = tmp_path / "projet"
    root.mkdir()
    await _git(root, "init", "-q", "-b", "main")
    await _git(root, "config", "user.email", "test@tessera.local")
    await _git(root, "config", "user.name", "Tessera test")
    (root / "README.md").write_text("# projet\n", encoding="utf-8")
    (root / "CLAUDE.md").write_text("# projet\n", encoding="utf-8")
    await _git(root, "add", "README.md", "CLAUDE.md")
    await _git(root, "commit", "-q", "-m", "init")
    return root


async def test_tracked_file_covered_by_exclude_stays_in_index(repo: Path) -> None:
    """A CLAUDE.md versioned by the repository survives the purge."""
    with (repo / ".git" / "info" / "exclude").open("a", encoding="utf-8") as f:
        f.write("CLAUDE.md\n")

    await GitWorkspaceService(repo)._purger_stage_ignoré()

    assert "CLAUDE.md" in (await _git(repo, "ls-files", "CLAUDE.md"))


async def test_newly_staged_ignored_file_is_still_removed(repo: Path) -> None:
    """A file absent from HEAD, staged then covered by .gitignore, is purged."""
    (repo / ".gitignore").write_text("*.db-wal\n", encoding="utf-8")
    (repo / "tessera.db-wal").write_bytes(b"\x00\x01")
    await _git(repo, "add", "-f", "tessera.db-wal")

    await GitWorkspaceService(repo)._purger_stage_ignoré()

    assert "tessera.db-wal" not in (await _git(repo, "ls-files"))


async def test_purge_on_repo_without_commit_keeps_old_behaviour(
    tmp_path: Path,
) -> None:
    """With no HEAD at all, ignored staged files are still removed."""
    root = tmp_path / "vide"
    root.mkdir()
    await _git(root, "init", "-q", "-b", "main")
    (root / ".gitignore").write_text("*.db-wal\n", encoding="utf-8")
    (root / "tessera.db-wal").write_bytes(b"\x00")
    await _git(root, "add", "-f", "tessera.db-wal")

    await GitWorkspaceService(root)._purger_stage_ignoré()

    assert "tessera.db-wal" not in (await _git(root, "ls-files"))
