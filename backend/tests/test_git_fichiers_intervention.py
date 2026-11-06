"""`fichiers_de_branche` et `fichiers_modifies` sur un vrai dépôt — ticket-854."""
import asyncio
from pathlib import Path

import pytest

from tessera.services.git_workspace import GitWorkspaceService


async def _git(cwd: Path, *args: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "git", *args, cwd=str(cwd), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    assert proc.returncode == 0, f"git {' '.join(args)} : {err.decode()}"
    return out.decode().strip()


def _ecrire(cwd: Path, fichier: str, contenu: str = "x\n") -> None:
    chemin = cwd / fichier
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(contenu, encoding="utf-8")


@pytest.fixture
async def depot(tmp_path: Path) -> Path:
    """A repository holding a project nested at `projects/p/`."""
    racine = tmp_path / "depot"
    racine.mkdir()
    await _git(racine, "init", "-q", "-b", "develop")
    await _git(racine, "config", "user.email", "test@tessera.local")
    await _git(racine, "config", "user.name", "Tessera test")
    _ecrire(racine, "projects/p/README.md")
    _ecrire(racine, "autre/a.txt")
    await _git(racine, "add", "-A")
    await _git(racine, "commit", "-q", "-m", "init")
    return racine


async def test_branch_files_are_relative_to_the_project_and_outside_ones_escape(depot: Path) -> None:
    await _git(depot, "checkout", "-q", "-b", "supervision-20261106-101500")
    _ecrire(depot, "projects/p/tickets/todo/ticket-1.md")
    _ecrire(depot, "autre/b.txt")
    await _git(depot, "add", "-A")
    await _git(depot, "commit", "-q", "-m", "work")

    fichiers = await GitWorkspaceService(depot / "projects" / "p").fichiers_de_branche(
        "develop", "supervision-20261106-101500"
    )

    assert sorted(fichiers) == ["../../autre/b.txt", "tickets/todo/ticket-1.md"]


async def test_modified_files_cover_untracked_edited_and_renamed(depot: Path) -> None:
    projet = depot / "projects" / "p"
    _ecrire(projet, "tickets/neuf.md")
    _ecrire(projet, "README.md", "change\n")
    await _git(depot, "mv", "autre/a.txt", "autre/renomme.txt")

    fichiers = await GitWorkspaceService(projet).fichiers_modifies()

    assert sorted(fichiers) == [
        "../../autre/a.txt", "../../autre/renomme.txt", "README.md", "tickets/neuf.md",
    ]


async def test_modified_files_of_a_clean_tree_is_empty(depot: Path) -> None:
    assert await GitWorkspaceService(depot / "projects" / "p").fichiers_modifies() == []
