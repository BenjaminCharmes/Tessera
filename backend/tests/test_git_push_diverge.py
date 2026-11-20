"""A diverged remote branch is never forced: the head goes under `<branch>-2`."""
import asyncio
from pathlib import Path

import pytest

from tessera.services.git_workspace import GitWorkspaceService


async def _git(cwd: Path, *args: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "git", *args, cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    assert proc.returncode == 0, err.decode()
    return out.decode()


class _Espion(GitWorkspaceService):
    """Records every git call that goes through `_run`."""

    appels: list[tuple[str, ...]]

    async def _run(self, *args: str) -> str:
        if not hasattr(self, "appels"):
            self.appels = []
        self.appels.append(args)
        return await super()._run(*args)


@pytest.fixture
async def depot(tmp_path: Path) -> tuple[Path, Path, str]:
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
    branch = await GitWorkspaceService(project).create_branch("ticket-1010", "reprise")
    (project / "a.py").write_text("a = 1\n", encoding="utf-8")
    await GitWorkspaceService(project).commit_all("feat: a")
    return project, remote, branch


async def _remote_sha(remote: Path, ref: str) -> str:
    return (await _git(remote, "rev-parse", f"refs/heads/{ref}")).strip()


async def _diverger(project: Path, branch: str) -> None:
    """Pushes the branch, then rewrites its commit so the head changes SHA."""
    await GitWorkspaceService(project).push_branch(branch)
    await _git(project, "commit", "--amend", "-q", "-m", "feat: a (rejoué)")


async def test_diverged_remote_gets_derived_name_and_stays_intact(
    depot: tuple[Path, Path, str],
) -> None:
    project, remote, branch = depot
    await _diverger(project, branch)
    original = await _remote_sha(remote, branch)
    local = (await _git(project, "rev-parse", branch)).strip()

    pousse = await GitWorkspaceService(project).push_branch(branch)

    assert pousse == f"{branch}-2"
    assert await _remote_sha(remote, f"{branch}-2") == local
    assert await _remote_sha(remote, branch) == original


async def test_second_push_reuses_derived_name_then_next_number(
    depot: tuple[Path, Path, str],
) -> None:
    project, remote, branch = depot
    await _diverger(project, branch)
    service = GitWorkspaceService(project)
    assert await service.push_branch(branch) == f"{branch}-2"

    # Un commit de plus : la tête descend du `-2`, il se pousse en avance rapide.
    (project / "b.py").write_text("b = 1\n", encoding="utf-8")
    await service.commit_all("chore: b")
    assert await service.push_branch(branch) == f"{branch}-2"

    # Une nouvelle réécriture diverge aussi du `-2` : on passe au `-3`.
    await _git(project, "commit", "--amend", "-q", "-m", "chore: b (rejoué)")
    assert await service.push_branch(branch) == f"{branch}-3"


async def test_descending_remote_pushes_under_its_own_name(
    depot: tuple[Path, Path, str],
) -> None:
    project, remote, branch = depot
    service = GitWorkspaceService(project)
    await service.push_branch(branch)
    (project / "c.py").write_text("c = 1\n", encoding="utf-8")
    await service.commit_all("feat: c")

    assert await service.push_branch(branch) == branch
    local = (await _git(project, "rev-parse", branch)).strip()
    assert await _remote_sha(remote, branch) == local


async def test_no_git_call_is_forced(depot: tuple[Path, Path, str]) -> None:
    project, _, branch = depot
    await _diverger(project, branch)
    espion = _Espion(project)

    await espion.push_branch(branch)

    assert any(a[0] == "push" for a in espion.appels)
    for appel in espion.appels:
        assert not any(
            a == "--force" or a.startswith("--force-with-lease") or a == "-f"
            or a.startswith("+")
            for a in appel
        )


async def test_pull_request_opens_from_the_derived_name() -> None:
    from tessera.services.github.github_workflow import GitHubWorkflowService

    class _Git:
        async def push_branch(self, branch_name: str) -> str:
            return f"{branch_name}-2"

        async def current_diff(self) -> str:
            return ""

        async def diff_de_branche(self, base: str, branch: str) -> str:
            return ""

        async def commits_depuis_base(self, base: str, branch: str) -> list[object]:
            return []

    class _GitHub:
        heads: list[str] = []

        async def create_pull_request(self, **kw: str) -> tuple[int, str]:
            self.heads.append(kw["head"])
            return 9, "https://example.test/pull/9"

    github = _GitHub()
    svc = GitHubWorkflowService(
        git_workspace=_Git(), github=github, base_branch="develop"  # type: ignore[arg-type]
    )

    result = await svc.open_pull_request(
        branch="ticket-1-x", ticket_id="ticket-1", ticket_title="t", ticket_body=""
    )

    assert github.heads == ["ticket-1-x-2"]
    assert result.branch == "ticket-1-x-2"
