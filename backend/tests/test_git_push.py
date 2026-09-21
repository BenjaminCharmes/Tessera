"""Pousser une branche — le maillon manquant, ticket-064."""
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


@pytest.fixture
async def repo_with_remote(tmp_path: Path) -> tuple[Path, Path]:
    """Un projet et un dépôt distant nu, tous deux locaux — pas de réseau."""
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
    return project, remote


async def test_pousse_la_branche_courante_sur_origin(
    repo_with_remote: tuple[Path, Path],
) -> None:
    # Le maillon manquant : `create-pr` demandait à GitHub une branche `head`
    # que rien n'avait jamais poussée.
    project, remote = repo_with_remote
    service = GitWorkspaceService(project)
    branch = await service.create_branch("ticket-042", "une-feature")
    (project / "nouveau.py").write_text("y = 2\n", encoding="utf-8")
    await service.commit_all("feat: ticket-042 — une feature")

    await service.push_branch(branch)

    assert branch in await _git(remote, "branch", "--list")


async def test_pousser_deux_fois_met_a_jour_la_branche(
    repo_with_remote: tuple[Path, Path],
) -> None:
    project, remote = repo_with_remote
    service = GitWorkspaceService(project)
    branch = await service.create_branch("ticket-043", "suite")
    (project / "a.py").write_text("a = 1\n", encoding="utf-8")
    await service.commit_all("feat: premier")
    await service.push_branch(branch)

    (project / "b.py").write_text("b = 2\n", encoding="utf-8")
    await service.commit_all("feat: second")
    await service.push_branch(branch)

    log = await _git(remote, "log", branch, "--format=%s")
    assert "feat: second" in log


async def test_pousser_sans_remote_echoue_clairement(tmp_path: Path) -> None:
    project = tmp_path / "sans-remote"
    project.mkdir()
    await _git(project, "init", "-q")
    await _git(project, "config", "user.email", "t@t.local")
    await _git(project, "config", "user.name", "t")
    (project / "f.py").write_text("x = 1\n", encoding="utf-8")
    await _git(project, "add", "f.py")
    await _git(project, "commit", "-q", "-m", "initial")

    service = GitWorkspaceService(project)

    with pytest.raises(GitCommandError):
        await service.push_branch("main")


async def test_le_push_n_est_jamais_force(repo_with_remote: tuple[Path, Path]) -> None:
    # Un push forcé sur le dépôt d'un utilisateur, a fortiori d'un client,
    # peut détruire du travail. La commande ne doit pas le permettre.
    import inspect

    source = inspect.getsource(GitWorkspaceService.push_branch)
    assert "--force" not in source
    assert "-f" not in source.split()
