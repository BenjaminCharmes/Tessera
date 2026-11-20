"""An empty leftover worktree folder does not block the next run — ticket-1003."""
import logging
from pathlib import Path

import pytest

from tessera.config import settings
from tessera.services.worktrees import run_worktree
from tessera.services.worktrees.run_worktree import RunWorktree, WorktreeOccupe, creer, supprimer
from tests.depot_worktree import BRANCHE, construire, git


@pytest.fixture
def checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    return construire(tmp_path, monkeypatch)


async def _creer(repo: Path) -> RunWorktree:
    return await creer(repo, repo, "demo", "ticket-1", BRANCHE, "develop")


def _racine() -> Path:
    return settings.ide_worktrees_dir / "demo" / "ticket-1"


async def test_creer_replaces_an_empty_unregistered_folder(
    checkout: Path, caplog: pytest.LogCaptureFixture
) -> None:
    _racine().mkdir(parents=True)
    with caplog.at_level(logging.INFO):
        wt = await _creer(checkout)
    assert git(wt.racine, "rev-parse", "--abbrev-ref", "HEAD") == BRANCHE
    assert any("run_worktree_dossier_vide_retire" in r.getMessage() for r in caplog.records)


async def test_creer_keeps_refusing_a_folder_that_holds_a_file(checkout: Path) -> None:
    racine = _racine()
    racine.mkdir(parents=True)
    (racine / "ignore.log").write_text("x", encoding="utf-8")
    with pytest.raises(WorktreeOccupe):
        await _creer(checkout)
    assert (racine / "ignore.log").read_text(encoding="utf-8") == "x"


async def test_supprimer_retries_the_rmdir_of_an_empty_leftover(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "ide_worktrees_dir", tmp_path / "worktrees")
    racine = _racine()
    racine.mkdir(parents=True)
    vrai_rmdir = Path.rmdir
    essais: list[Path] = []

    def rmdir(self: Path) -> None:
        essais.append(self)
        if len(essais) == 1:
            raise PermissionError("poignée ouverte")
        vrai_rmdir(self)

    async def git_muet(_cwd: Path, *_args: str) -> str:
        return ""

    monkeypatch.setattr(run_worktree, "run_git", git_muet)
    monkeypatch.setattr(run_worktree, "_etat", lambda _r: _vide())
    monkeypatch.setattr(run_worktree, "_ATTENTE_DOSSIER_S", 0)
    monkeypatch.setattr(Path, "rmdir", rmdir)
    await supprimer(RunWorktree(racine=racine, projet=racine, branche=BRANCHE), tmp_path)
    assert not racine.exists()
    assert len(essais) == 2


async def test_supprimer_logs_without_raising_when_the_folder_stays(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(settings, "ide_worktrees_dir", tmp_path / "worktrees")
    racine = _racine()
    racine.mkdir(parents=True)

    async def git_muet(_cwd: Path, *_args: str) -> str:
        return ""

    def refuse(self: Path) -> None:
        raise PermissionError("poignée ouverte")

    monkeypatch.setattr(run_worktree, "run_git", git_muet)
    monkeypatch.setattr(run_worktree, "_etat", lambda _r: _vide())
    monkeypatch.setattr(run_worktree, "_ATTENTE_DOSSIER_S", 0)
    monkeypatch.setattr(Path, "rmdir", refuse)
    with caplog.at_level(logging.WARNING):
        await supprimer(RunWorktree(racine=racine, projet=racine, branche=BRANCHE), tmp_path)
    assert racine.exists()
    assert any("run_worktree_dossier_restant" in r.getMessage() for r in caplog.records)


async def _vide() -> str:
    return ""
