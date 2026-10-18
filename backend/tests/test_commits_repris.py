"""Le nombre de commits qu'une branche reprise porte — ticket-497."""
from pathlib import Path

from tessera.services.git_workspace import GitWorkspaceService
from tests.test_git_workspace import _git, repo  # noqa: F401  (fixture `repo`)


async def _commit(service: GitWorkspaceService, repo_path: Path, name: str) -> None:
    (repo_path / name).write_text(f"{name}\n", encoding="utf-8")
    await service.commit_all(f"feat: {name}")


async def test_fresh_branch_carries_no_resumed_commit(repo: Path) -> None:
    service = GitWorkspaceService(repo)
    await service.create_branch("ticket-497", "fresh")
    assert service.commits_repris == 0


async def test_resumed_branch_counts_its_commits_past_the_fork_point(repo: Path) -> None:
    service = GitWorkspaceService(repo)
    await service.create_branch("ticket-497", "resumed")
    await _commit(service, repo, "a.py")
    await _commit(service, repo, "b.py")
    base = service._base_ref
    await _git(repo, "checkout", "-q", "-")

    second = GitWorkspaceService(repo)
    second._base_ref = base
    await second.create_branch("ticket-497", "resumed")

    assert second.commits_repris == 2


async def test_resumed_branch_without_new_commit_counts_zero(repo: Path) -> None:
    service = GitWorkspaceService(repo)
    await service.create_branch("ticket-497", "empty")
    base = service._base_ref
    await _git(repo, "checkout", "-q", "-")

    second = GitWorkspaceService(repo)
    second._base_ref = base
    await second.create_branch("ticket-497", "empty")

    assert second.commits_repris == 0


async def test_branch_replayed_on_an_advanced_base_keeps_its_count(repo: Path) -> None:
    await _git(repo, "checkout", "-q", "-b", "ticket-497-replayed")
    service = GitWorkspaceService(repo)
    await _commit(service, repo, "work.py")
    await _git(repo, "checkout", "-q", "-")
    (repo / "advance.py").write_text("y = 2\n", encoding="utf-8")
    await _git(repo, "add", "advance.py")
    await _git(repo, "commit", "-q", "-m", "chore: base advances")

    resumed = GitWorkspaceService(repo)
    await resumed.create_branch("ticket-497", "replayed")

    assert resumed.commits_repris == 1


async def test_branch_renamed_stale_after_a_conflict_counts_zero(repo: Path) -> None:
    await _git(repo, "checkout", "-q", "-b", "ticket-497-conflict")
    (repo / "shared.py").write_text("version = 'ticket'\n", encoding="utf-8")
    await _git(repo, "add", "shared.py")
    await _git(repo, "commit", "-q", "-m", "feat: ticket writes shared.py")
    await _git(repo, "checkout", "-q", "-")
    (repo / "shared.py").write_text("version = 'base'\n", encoding="utf-8")
    await _git(repo, "add", "shared.py")
    await _git(repo, "commit", "-q", "-m", "chore: base writes shared.py")

    resumed = GitWorkspaceService(repo)
    await resumed.create_branch("ticket-497", "conflict")

    assert resumed.commits_repris == 0
