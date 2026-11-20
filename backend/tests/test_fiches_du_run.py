"""Tickets a design run writes under tickets/todo/ ride with its commit and diff — ticket-1026."""
import asyncio
from pathlib import Path

import pytest

from tessera.services.git_workspace import GitWorkspaceService

_FICHE = "tickets/todo/ticket-900-x.md"


async def _git(cwd: Path, *args: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "git", *args, cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    assert proc.returncode == 0, err.decode()
    return out.decode().strip()


@pytest.fixture
async def projet(tmp_path: Path) -> Path:
    await _git(tmp_path, "init", "-q", "-b", "main")
    await _git(tmp_path, "config", "user.email", "test@tessera.local")
    await _git(tmp_path, "config", "user.name", "Tessera test")
    (tmp_path / "tickets" / "todo").mkdir(parents=True)
    (tmp_path / "tickets" / "todo" / ".gitkeep").write_text("", encoding="utf-8")
    (tmp_path / "base.txt").write_text("base\n", encoding="utf-8")
    await _git(tmp_path, "add", "-A")
    await _git(tmp_path, "commit", "-q", "-m", "init")
    return tmp_path


async def _demarrer(projet: Path) -> GitWorkspaceService:
    service = GitWorkspaceService(projet)
    await service.create_branch("900", "x")
    return service


@pytest.mark.parametrize("message", ["feat: done", "chore: unapproved work"])
async def test_created_ticket_is_in_the_run_commit(projet: Path, message: str) -> None:
    service = await _demarrer(projet)
    (projet / _FICHE).write_text("# ticket-900\n", encoding="utf-8")

    sha = await service.commit_all(message)

    assert sha is not None
    fichiers = await _git(projet, "show", "--name-only", "--format=", sha)
    assert _FICHE in fichiers.splitlines()
    assert await service.fichiers_non_suivis_laisses() == ()


async def test_diff_for_the_validator_holds_the_ticket_content(projet: Path) -> None:
    service = await _demarrer(projet)
    (projet / _FICHE).write_text("# ticket-900\ncritere unique\n", encoding="utf-8")

    diff = await service.diff_depuis_base()
    courant = await service.current_diff()

    for texte in (diff, courant):
        assert "critere unique" in texte
    assert await _git(projet, "status", "--porcelain") == "?? " + _FICHE


async def test_untracked_file_elsewhere_is_still_reported(projet: Path) -> None:
    service = await _demarrer(projet)
    (projet / _FICHE).write_text("# ticket-900\n", encoding="utf-8")
    (projet / "src").mkdir()
    (projet / "src" / "x.ts").write_text("export {}\n", encoding="utf-8")

    laisses = await service.fichiers_non_suivis_laisses()
    diff = await service.diff_depuis_base()

    assert laisses == ("src/x.ts",)
    assert "export {}" in diff
