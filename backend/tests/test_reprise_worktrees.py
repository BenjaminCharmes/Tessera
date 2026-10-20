"""Recovery of run worktrees left by a backend stop — ticket-520.

Throwaway repository with a local origin (`depot_worktree`); the checkout sits
under `workspace`, so it is the project the recovery looks at.
"""
import logging
import shutil
from pathlib import Path

import pytest

from tessera.config import settings
from tessera.services import reprise_worktrees
from tessera.services.git_workspace import GitCommandError
from tessera.services.run_worktree import RunWorktree, creer
from tessera.services.reprise_worktrees import reprendre_worktrees_orphelins
from tests.depot_worktree import BRANCHE, construire, git, lier


@pytest.fixture
def checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    return construire(tmp_path, monkeypatch)


async def _worktree(repo: Path, ticket: str = "ticket-1", branche: str = BRANCHE) -> RunWorktree:
    return await creer(repo, repo, "demo", ticket, branche, "develop")


async def _reprendre(repo: Path) -> None:
    await reprendre_worktrees_orphelins(repo.parent, settings.ide_worktrees_dir)


def _etat_du_checkout(repo: Path) -> tuple[str, str, str]:
    return (
        git(repo, "rev-parse", "--abbrev-ref", "HEAD"),
        git(repo, "rev-parse", "HEAD"),
        git(repo, "status", "--porcelain", "--ignored"),
    )


async def test_dirty_worktree_is_committed_as_unapproved_work_then_removed(
    checkout: Path,
) -> None:
    wt = await _worktree(checkout)
    (wt.racine / "suivi.txt").write_text("modifie", encoding="utf-8")
    (wt.racine / "nouveau.txt").write_text("nouveau", encoding="utf-8")
    (wt.racine / "cache").mkdir()
    (wt.racine / "cache" / "ignore.txt").write_text("x", encoding="utf-8")

    await _reprendre(checkout)

    assert not wt.racine.exists()
    sujet = git(checkout, "log", "-1", "--format=%s", BRANCHE)
    # Le tiret long n'est pas comparé : le helper `git` décode avec l'encodage local.
    assert sujet.startswith("chore: ticket-1 ")
    assert sujet.endswith("unapproved work (run interrupted by a backend stop)")
    fichiers = git(checkout, "show", "--name-only", "--format=", BRANCHE).splitlines()
    assert sorted(fichiers) == ["nouveau.txt", "suivi.txt"]
    assert wt.racine.as_posix() not in git(checkout, "worktree", "list")


async def test_clean_worktree_is_removed_without_a_commit(checkout: Path) -> None:
    wt = await _worktree(checkout)
    avant = git(checkout, "rev-parse", BRANCHE)

    await _reprendre(checkout)

    assert not wt.racine.exists()
    assert git(checkout, "rev-parse", BRANCHE) == avant


async def test_a_registration_whose_folder_vanished_is_pruned(checkout: Path) -> None:
    wt = await _worktree(checkout)
    shutil.rmtree(wt.racine)
    assert "ticket-1" in git(checkout, "worktree", "list")

    await _reprendre(checkout)

    assert "ticket-1" not in git(checkout, "worktree", "list")


async def test_a_failed_commit_keeps_the_folder_and_the_startup_goes_on(
    checkout: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    sale = await _worktree(checkout)
    propre = await _worktree(checkout, "ticket-2", "ticket-2-demo")
    (sale.racine / "travail.txt").write_text("a sauver", encoding="utf-8")
    vrai_run_git = reprise_worktrees.run_git

    async def _commit_refuse(cwd: Path, *args: str) -> str:
        if args[0] == "commit":
            raise GitCommandError(["git", *args], 1, "refus de test")
        return await vrai_run_git(cwd, *args)

    monkeypatch.setattr(reprise_worktrees, "run_git", _commit_refuse)
    with caplog.at_level(logging.WARNING, logger="tessera.services.reprise_worktrees"):
        await _reprendre(checkout)

    assert (sale.racine / "travail.txt").read_text(encoding="utf-8") == "a sauver"
    assert any(getattr(r, "raison", "") == "echec" for r in caplog.records)
    assert not propre.racine.exists()


async def test_a_linked_node_modules_survives_the_removal(checkout: Path) -> None:
    wt = await _worktree(checkout)
    lier(checkout / "node_modules", wt.racine / "node_modules")
    (wt.racine / "nouveau.txt").write_text("nouveau", encoding="utf-8")

    await _reprendre(checkout)

    assert not wt.racine.exists()
    temoin = checkout / "node_modules" / "pkg" / "index.js"
    assert temoin.read_text(encoding="utf-8") == "temoin"
    assert "node_modules" not in git(checkout, "show", "--name-only", "--format=", BRANCHE)


async def test_the_checkout_is_the_same_before_and_after(checkout: Path) -> None:
    wt = await _worktree(checkout)
    (wt.racine / "nouveau.txt").write_text("nouveau", encoding="utf-8")
    avant = _etat_du_checkout(checkout)

    await _reprendre(checkout)

    assert _etat_du_checkout(checkout) == avant
    assert "pas-suivi.txt" in git(checkout, "status", "--porcelain")


async def test_a_folder_no_repository_registers_is_left_and_logged(
    checkout: Path, caplog: pytest.LogCaptureFixture
) -> None:
    inconnu = settings.ide_worktrees_dir / "demo" / "ticket-9"
    inconnu.mkdir(parents=True)
    (inconnu / "a.txt").write_text("a", encoding="utf-8")

    with caplog.at_level(logging.WARNING, logger="tessera.services.reprise_worktrees"):
        await _reprendre(checkout)

    assert (inconnu / "a.txt").read_text(encoding="utf-8") == "a"
    assert any(getattr(r, "raison", "") == "inconnu_des_depots" for r in caplog.records)


async def test_a_missing_worktrees_folder_is_not_an_error(checkout: Path) -> None:
    assert not settings.ide_worktrees_dir.exists()
    await _reprendre(checkout)
