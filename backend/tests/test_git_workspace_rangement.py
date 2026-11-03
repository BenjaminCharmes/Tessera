"""`commits_hors_rangement` sur un vrai dépôt — ticket-492.

Couverture :
- un commit de code après le SHA approuvé est signalé ;
- des commits qui ne touchent que `tickets/` et `memory/pipeline-log.md` ne le sont pas ;
- un commit mixte (rangement + code) est signalé ;
- un merge commit est signalé ;
- une tête qui ne descend plus du SHA approuvé est signalée ;
- un projet imbriqué dans le dépôt (`git_root: ancestor`) : les chemins se lisent
  relativement au projet ;
- `head_sha` et `sha_distant`.
"""
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
    assert proc.returncode == 0, f"git {' '.join(args)} : {err.decode()}"
    return out.decode().strip()


async def _commit(cwd: Path, fichier: str, contenu: str) -> str:
    chemin = cwd / fichier
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(contenu, encoding="utf-8")
    await _git(cwd, "add", fichier)
    await _git(cwd, "commit", "-q", "-m", f"change {fichier}")
    return await _git(cwd, "rev-parse", "HEAD")


@pytest.fixture
async def repo(tmp_path: Path) -> Path:
    root = tmp_path / "depot"
    root.mkdir()
    await _git(root, "init", "-q", "-b", "main")
    await _git(root, "config", "user.email", "test@tessera.local")
    await _git(root, "config", "user.name", "Tessera test")
    await _commit(root, "README.md", "# depot\n")
    await _git(root, "checkout", "-q", "-b", "ticket-001-slug")
    return root


async def test_code_commit_is_reported(repo: Path) -> None:
    approuve = await _commit(repo, "code.py", "x = 1\n")
    intrus = await _commit(repo, "code.py", "x = 2\n")

    assert await GitWorkspaceService(repo).commits_hors_rangement(approuve) == [intrus]


async def test_bookkeeping_commits_are_not_reported(repo: Path) -> None:
    approuve = await _commit(repo, "code.py", "x = 1\n")
    await _commit(repo, "tickets/in-progress/ticket-001.md", "---\n---\n")
    await _commit(repo, "memory/pipeline-log.md", "ligne\n")

    assert await GitWorkspaceService(repo).commits_hors_rangement(approuve) == []


async def test_no_commit_after_approval_is_not_reported(repo: Path) -> None:
    approuve = await _commit(repo, "code.py", "x = 1\n")

    assert await GitWorkspaceService(repo).commits_hors_rangement(approuve) == []


async def test_mixed_commit_is_reported(repo: Path) -> None:
    approuve = await _commit(repo, "code.py", "x = 1\n")
    (repo / "memory").mkdir()
    (repo / "memory" / "pipeline-log.md").write_text("ligne\n", encoding="utf-8")
    (repo / "code.py").write_text("x = 3\n", encoding="utf-8")
    await _git(repo, "add", "memory/pipeline-log.md", "code.py")
    await _git(repo, "commit", "-q", "-m", "mixte")
    mixte = await _git(repo, "rev-parse", "HEAD")

    assert await GitWorkspaceService(repo).commits_hors_rangement(approuve) == [mixte]


async def test_merge_commit_is_reported(repo: Path) -> None:
    approuve = await _commit(repo, "code.py", "x = 1\n")
    await _git(repo, "checkout", "-q", "-b", "autre", "main")
    await _commit(repo, "autre.py", "y = 1\n")
    await _git(repo, "checkout", "-q", "ticket-001-slug")
    await _git(repo, "merge", "--no-ff", "-q", "-m", "merge", "autre")
    fusion = await _git(repo, "rev-parse", "HEAD")

    intrus = await GitWorkspaceService(repo).commits_hors_rangement(approuve)

    assert fusion in intrus


async def test_head_not_descending_from_approved_is_reported(repo: Path) -> None:
    await _commit(repo, "code.py", "x = 1\n")
    approuve = await _commit(repo, "code.py", "x = 2\n")
    await _git(repo, "reset", "-q", "--hard", "HEAD~1")
    tete = await _commit(repo, "code.py", "x = 9\n")

    assert await GitWorkspaceService(repo).commits_hors_rangement(approuve) == [tete]


async def test_nested_project_reads_paths_relative_to_project(repo: Path) -> None:
    projet = repo / "projects" / "demo"
    projet.mkdir(parents=True)
    approuve = await _commit(repo, "projects/demo/code.py", "x = 1\n")
    await _commit(repo, "projects/demo/tickets/done/ticket-001.md", "---\n---\n")
    intrus = await _commit(repo, "projects/demo/code.py", "x = 2\n")

    reste = await GitWorkspaceService(projet).commits_hors_rangement(approuve)

    assert reste == [intrus]


async def test_unknown_sha_raises_so_the_caller_fails_closed(repo: Path) -> None:
    with pytest.raises(Exception):
        await GitWorkspaceService(repo).commits_hors_rangement("f" * 40)


async def test_head_sha_is_the_full_sha(repo: Path) -> None:
    tete = await _commit(repo, "code.py", "x = 1\n")

    assert await GitWorkspaceService(repo).head_sha() == tete


async def test_sha_distant_reads_the_pushed_head(repo: Path, tmp_path: Path) -> None:
    distant = tmp_path / "distant.git"
    distant.mkdir()
    await _git(distant, "init", "-q", "--bare")
    await _git(repo, "remote", "add", "origin", str(distant))
    service = GitWorkspaceService(repo)
    assert await service.sha_distant("ticket-001-slug") is None

    tete = await _commit(repo, "code.py", "x = 1\n")
    await _git(repo, "push", "-q", "origin", "ticket-001-slug")

    assert await service.sha_distant("ticket-001-slug") == tete
