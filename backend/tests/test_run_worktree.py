"""Run worktree: create, resume and remove, on a throwaway repository with a local origin."""
import subprocess
import sys
from pathlib import Path

import pytest

from tessera.config import settings
from tessera.services.run_worktree import (
    BrancheDejaExtraite,
    CheminRefuse,
    RunWorktree,
    TravailNonSauve,
    WorktreeOccupe,
    creer,
    supprimer,
)

BRANCHE = "ticket-1-demo"


def _git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com",
         "-c", "commit.gpgsign=false", *args],
        cwd=cwd, check=True, capture_output=True, text=True,
    )
    return result.stdout.strip()


def _commit(repo: Path, nom: str) -> None:
    (repo / nom).parent.mkdir(parents=True, exist_ok=True)
    (repo / nom).write_text(nom, encoding="utf-8")
    _git(repo, "add", nom)
    _git(repo, "commit", "-m", f"add {nom}")


@pytest.fixture
def checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    base = tmp_path.resolve()
    origin = base / "origin.git"
    origin.mkdir()
    _git(origin, "init", "--bare", "-b", "develop")
    repo = base / "checkout"
    repo.mkdir()
    _git(repo, "init", "-b", "develop")
    _commit(repo, "README.md")
    _commit(repo, "projects/demo/CLAUDE.md")
    _git(repo, "remote", "add", "origin", str(origin))
    _git(repo, "push", "origin", "develop")
    monkeypatch.setattr(settings, "ide_worktrees_dir", base / "worktrees")
    return repo


async def _creer(repo: Path, branche: str = BRANCHE) -> RunWorktree:
    return await creer(repo, repo, "demo", "ticket-1", branche, "develop")


async def test_creer_builds_the_worktree_on_the_branch_at_the_remote_base(
    checkout: Path,
) -> None:
    # Un commit local non poussé : le worktree doit partir de origin/develop, pas de lui.
    _commit(checkout, "local-only.txt")
    attendu = _git(checkout, "rev-parse", "origin/develop")
    wt = await _creer(checkout)
    assert wt.racine == settings.ide_worktrees_dir / "demo" / "ticket-1"
    assert wt.branche == BRANCHE
    assert _git(wt.racine, "rev-parse", "--abbrev-ref", "HEAD") == BRANCHE
    assert _git(wt.racine, "rev-parse", "HEAD") == attendu
    assert not (wt.racine / "local-only.txt").exists()


async def test_creer_does_not_carry_what_is_written_in_the_checkout(
    checkout: Path,
) -> None:
    (checkout / "a-la-main.md").write_text("humain", encoding="utf-8")
    wt = await _creer(checkout)
    assert not (wt.racine / "a-la-main.md").exists()
    assert (checkout / "a-la-main.md").exists()


async def test_creer_twice_resumes_a_clean_worktree(checkout: Path) -> None:
    premier = await _creer(checkout)
    second = await _creer(checkout)
    assert second == premier
    assert _git(second.racine, "rev-parse", "--abbrev-ref", "HEAD") == BRANCHE


async def test_creer_refuses_a_folder_that_is_not_the_worktree(checkout: Path) -> None:
    occupe = settings.ide_worktrees_dir / "demo" / "ticket-1"
    occupe.mkdir(parents=True)
    with pytest.raises(WorktreeOccupe):
        await _creer(checkout)


async def test_creer_reports_a_branch_already_checked_out_without_forcing(
    checkout: Path,
) -> None:
    _git(checkout, "checkout", "-b", BRANCHE)
    with pytest.raises(BrancheDejaExtraite) as exc:
        await _creer(checkout)
    assert exc.value.branche == BRANCHE
    assert not (settings.ide_worktrees_dir / "demo" / "ticket-1").exists()
    assert _git(checkout, "rev-parse", "--abbrev-ref", "HEAD") == BRANCHE


async def test_supprimer_removes_a_clean_worktree_and_its_registration(
    checkout: Path,
) -> None:
    wt = await _creer(checkout)
    await supprimer(wt, checkout)
    assert not wt.racine.exists()
    assert "ticket-1" not in _git(checkout, "worktree", "list", "--porcelain")
    # La branche, elle, reste : c'est ce que le run a produit.
    assert BRANCHE in _git(checkout, "branch", "--list", BRANCHE)


async def test_supprimer_refuses_a_dirty_worktree_and_leaves_it(checkout: Path) -> None:
    wt = await _creer(checkout)
    (wt.racine / "pas-sauve.txt").write_text("x", encoding="utf-8")
    with pytest.raises(TravailNonSauve) as exc:
        await supprimer(wt, checkout)
    assert "pas-sauve.txt" in str(exc.value)
    assert (wt.racine / "pas-sauve.txt").exists()
    assert "ticket-1" in _git(checkout, "worktree", "list", "--porcelain")


@pytest.mark.skipif(sys.platform != "win32", reason="MAX_PATH is a Windows limit")
async def test_creer_handles_a_path_longer_than_260_characters(checkout: Path) -> None:
    # Le fichier est inscrit dans l'index sans passer par le disque du checkout.
    profond = "/".join(["d" * 80] * 3) + "/fichier.txt"
    blob = subprocess.run(
        ["git", "hash-object", "-w", "--stdin"], cwd=checkout, input="long",
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    _git(checkout, "update-index", "--add", "--cacheinfo", f"100644,{blob},{profond}")
    _git(checkout, "commit", "-m", "add a deep file")
    _git(checkout, "push", "origin", "develop")
    wt = await _creer(checkout)
    try:
        assert len(str(wt.racine / profond)) > 260
        # Le préfixe `\\?\` : c'est Python, ici, qui n'a pas la dispense de git.
        assert Path("\\\\?\\" + str(wt.racine / profond)).is_file()
    finally:
        subprocess.run(
            ["git", "-c", "core.longpaths=true", "worktree", "remove", "--force",
             str(wt.racine)],
            cwd=checkout, check=False, capture_output=True,
        )


async def test_projet_points_at_the_subfolder_for_an_ancestor_project(
    checkout: Path,
) -> None:
    wt = await creer(checkout, checkout / "projects" / "demo", "demo", "ticket-1",
                     BRANCHE, "develop")
    assert wt.projet == wt.racine / "projects" / "demo"
    assert (wt.projet / "CLAUDE.md").is_file()


async def test_projet_is_the_root_when_the_project_is_its_own_repository(
    checkout: Path,
) -> None:
    wt = await _creer(checkout)
    assert wt.projet == wt.racine


def test_only_the_run_wiring_imports_run_worktree() -> None:
    # Le branchement dans le run est le ticket-519 : ces quatre modules, et eux seuls.
    src = Path(__file__).resolve().parent.parent / "src" / "tessera"
    # Le module et son satellite de peuplement (ticket-523) ne comptent pas comme appelants.
    # La reprise au démarrage (ticket-520) retire des worktrees sans lancer de run :
    # elle ne compte pas comme un branchement.
    propres = {
        src / "services" / "run_worktree.py",
        src / "services" / "run_worktree_populate.py",
        src / "services" / "reprise_worktrees.py",
    }
    appelants = sorted(
        fichier.relative_to(src).as_posix()
        for fichier in src.rglob("*.py")
        if fichier not in propres and "run_worktree" in fichier.read_text(encoding="utf-8")
    )
    assert appelants == [
        "routers/orchestrator.py",
        "services/orchestrator.py",
        "services/pipeline_stages.py",
        "services/run_dans_worktree.py",
    ]


async def test_creer_leaves_the_checkout_on_its_branch_with_its_tree_untouched(
    checkout: Path,
) -> None:
    avant = _git(checkout, "rev-parse", "HEAD")
    await _creer(checkout)
    assert _git(checkout, "rev-parse", "--abbrev-ref", "HEAD") == "develop"
    assert _git(checkout, "rev-parse", "HEAD") == avant
    assert _git(checkout, "status", "--porcelain") == ""


@pytest.mark.parametrize(
    ("project_id", "ticket_id"),
    [("../x", "ticket-1"), ("demo", "../ticket-1"), ("demo", "ticket-1/../../x"),
     ("/abs", "ticket-1"), ("demo", "C:x"), ("..", "ticket-1"), ("demo", "1")],
)
async def test_creer_refuses_an_id_that_could_leave_the_worktrees_folder(
    checkout: Path, project_id: str, ticket_id: str
) -> None:
    with pytest.raises(CheminRefuse):
        await creer(checkout, checkout, project_id, ticket_id, BRANCHE, "develop")
    assert not settings.ide_worktrees_dir.exists() or not any(settings.ide_worktrees_dir.iterdir())


async def test_creer_refuses_a_symlink_that_leads_outside(
    checkout: Path, tmp_path: Path
) -> None:
    dehors = tmp_path / "dehors"
    dehors.mkdir()
    settings.ide_worktrees_dir.mkdir(parents=True)
    try:
        (settings.ide_worktrees_dir / "demo").symlink_to(dehors, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks unavailable on this machine")
    with pytest.raises(CheminRefuse):
        await _creer(checkout)
    assert list(dehors.iterdir()) == []


async def test_creer_refuses_a_branch_that_reads_as_an_option(checkout: Path) -> None:
    with pytest.raises(CheminRefuse):
        await _creer(checkout, branche="--force")


async def test_supprimer_refuses_a_root_outside_the_worktrees_folder(
    checkout: Path, tmp_path: Path
) -> None:
    ailleurs = tmp_path / "ailleurs"
    ailleurs.mkdir()
    (ailleurs / "garde.txt").write_text("ne pas effacer", encoding="utf-8")
    with pytest.raises(CheminRefuse):
        await supprimer(RunWorktree(racine=ailleurs, projet=ailleurs, branche=BRANCHE), checkout)
    assert (ailleurs / "garde.txt").exists()
