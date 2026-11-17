"""A link in a run tree is refused before anything is indexed (audit 17/11, C2).

Junction on Windows, symlink elsewhere: git follows the first, so `add -A` would
index the target and `diff` would show it.
"""
from pathlib import Path

import pytest

from tessera.config import settings
from tessera.services.git_workspace import GitWorkspaceService
from tessera.services.git_workspace.liens import LienNonDeclare, est_lien_suivi, trouver_liens
from tessera.services.pipeline.reprise_worktrees import reprendre_worktrees_orphelins
from tessera.services.worktrees.run_worktree import creer
from tests.depot_worktree import BRANCHE, construire, git, lier


@pytest.fixture
def checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    return construire(tmp_path, monkeypatch)


def _cible_exterieure(checkout: Path) -> Path:
    dehors = checkout.parent / "dehors"
    dehors.mkdir()
    (dehors / "secret.txt").write_text("ne pas indexer", encoding="utf-8")
    return dehors


def test_trouver_liens_names_a_link_without_entering_it(checkout: Path) -> None:
    dehors = _cible_exterieure(checkout)
    (checkout / "docs").mkdir()
    lier(dehors, checkout / "docs" / "x")

    assert trouver_liens(checkout) == ["docs/x"]


async def test_commit_all_refuses_an_undeclared_link_and_indexes_nothing(checkout: Path) -> None:
    lier(_cible_exterieure(checkout), checkout / "lien")
    (checkout / "travail.txt").write_text("ok", encoding="utf-8")
    service = GitWorkspaceService(checkout)

    with pytest.raises(LienNonDeclare, match="lien"):
        await service.commit_all("feat: x")

    assert git(checkout, "diff", "--cached", "--name-only") == ""


async def test_diffs_refuse_an_undeclared_link(checkout: Path) -> None:
    lier(_cible_exterieure(checkout), checkout / "lien")
    service = GitWorkspaceService(checkout)

    with pytest.raises(LienNonDeclare):
        await service.current_diff()
    assert "secret.txt" not in git(checkout, "ls-files", "--cached")


async def test_a_link_git_ignores_does_not_block(checkout: Path) -> None:
    # `cache/` est ignoré par le `.gitignore` du dépôt : c'est la forme d'un lien de `populate`.
    (checkout / "cache" / "a.txt").unlink()
    (checkout / "cache").rmdir()
    lier(_cible_exterieure(checkout), checkout / "cache")
    (checkout / "travail.txt").write_text("ok", encoding="utf-8")
    service = GitWorkspaceService(checkout)

    assert await service.commit_all("feat: x")
    fichiers = git(checkout, "show", "--name-only", "--format=", "HEAD").splitlines()
    assert "travail.txt" in fichiers
    assert not any("secret.txt" in f or f.startswith("cache") for f in fichiers)


def _remplacer_un_dossier_suivi_par_un_lien(checkout: Path) -> None:
    (checkout / "docs").mkdir()
    (checkout / "docs" / "a.txt").write_text("suivi", encoding="utf-8")
    git(checkout, "add", "docs/a.txt")
    git(checkout, "commit", "-m", "add docs")
    (checkout / "docs" / "a.txt").unlink()
    (checkout / "docs").rmdir()
    lier(_cible_exterieure(checkout), checkout / "docs")


async def test_a_junction_replacing_a_tracked_folder_is_refused(checkout: Path) -> None:
    _remplacer_un_dossier_suivi_par_un_lien(checkout)
    service = GitWorkspaceService(checkout)

    with pytest.raises(LienNonDeclare, match="docs"):
        await service.commit_all("feat: x")

    assert "secret.txt" not in git(checkout, "ls-files", "--cached")


def test_est_lien_suivi_requires_the_exact_path_as_a_symlink() -> None:
    sortie = "\0".join(["120000 abc 0\tlien", "100644 def 0\tdocs/a.txt", ""])

    assert est_lien_suivi(sortie, "lien")
    assert not est_lien_suivi(sortie, "docs")


async def test_reprise_refuses_to_commit_a_tree_with_an_undeclared_link(checkout: Path) -> None:
    wt = await creer(checkout, checkout, "demo", "ticket-1", BRANCHE, "develop")
    lier(_cible_exterieure(checkout), wt.racine / "lien")
    (wt.racine / "travail.txt").write_text("a sauver", encoding="utf-8")
    avant = git(checkout, "rev-parse", BRANCHE)

    await reprendre_worktrees_orphelins(checkout.parent, settings.ide_worktrees_dir)

    assert wt.racine.exists()
    assert git(checkout, "rev-parse", BRANCHE) == avant
