"""Vider un worktree ne bloque pas la boucle d'événements — ticket-551."""
import shutil
import threading
from pathlib import Path

import pytest

from tessera.config import settings
from tessera.services import run_worktree
from tessera.services.git_workspace import GitCommandError
from tessera.services.run_worktree import RunWorktree, supprimer
from tests.depot_worktree import BRANCHE


async def test_supprimer_empties_the_folder_off_the_event_loop_thread(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "ide_worktrees_dir", tmp_path / "worktrees")
    racine = settings.ide_worktrees_dir / "demo" / "ticket-1"
    (racine / "node_modules").mkdir(parents=True)
    fils: list[int] = []

    async def git(_cwd: Path, *args: str) -> str:
        if args[:2] == ("worktree", "remove"):
            raise GitCommandError(["git", *args], 1, "Directory not empty")
        return ""

    async def propre(_racine: Path) -> str:
        return ""

    def arbre(*_args: object, **_kwargs: object) -> None:
        fils.append(threading.get_ident())

    monkeypatch.setattr(run_worktree, "run_git", git)
    monkeypatch.setattr(run_worktree, "_etat", propre)
    monkeypatch.setattr(shutil, "rmtree", arbre)
    await supprimer(RunWorktree(racine=racine, projet=racine, branche=BRANCHE), tmp_path)
    assert fils and fils[0] != threading.get_ident()
