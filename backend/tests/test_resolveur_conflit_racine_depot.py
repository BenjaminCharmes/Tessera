"""The conflict resolver checks and stages files from the repository root — ticket-592.

Run on a real git repository where the project is a sub-folder
(`git_root: ancestor`), conflicting on a file *outside* the project folder:
`git diff --name-only` paths start at the repository root, not at the project.
"""

import asyncio
import json
from pathlib import Path

import pytest

from tessera.services.git_workspace import GitWorkspaceService

_FICHIER = "frontend/Piece.tsx"


async def _git(cwd: Path, *args: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    assert proc.returncode == 0, stderr.decode()
    return stdout.decode()


async def _commit(root: Path, contenu: str, message: str) -> None:
    (root / _FICHIER).write_text(contenu, encoding="utf-8")
    await _git(root, "add", _FICHIER)
    await _git(root, "commit", "-q", "-m", message)


@pytest.fixture
async def depot(tmp_path: Path) -> tuple[Path, Path]:
    """A repository holding a project sub-folder, in conflict on a root-level file."""
    racine = tmp_path / "depot"
    projet = racine / "projects" / "demo"
    projet.mkdir(parents=True)
    (racine / "frontend").mkdir()
    await _git(racine, "init", "-q", "-b", "main")
    await _git(racine, "config", "user.email", "test@tessera.local")
    await _git(racine, "config", "user.name", "Tessera test")
    (projet / "agents.json").write_text(
        json.dumps({"git_root": "ancestor"}), encoding="utf-8"
    )
    await _git(racine, "add", "projects/demo/agents.json")
    await _commit(racine, "import a\n", "init")
    await _git(racine, "checkout", "-q", "-b", "ticket-592-x")
    await _commit(racine, "import branche\n", "feat: branche")
    await _git(racine, "checkout", "-q", "main")
    await _commit(racine, "import base\n", "chore: base")
    await _git(racine, "checkout", "-q", "ticket-592-x")
    return racine, projet


async def test_a_conflict_outside_the_project_folder_is_resolved(
    depot: tuple[Path, Path],
) -> None:
    racine, projet = depot
    service = GitWorkspaceService(projet)
    appels: list[tuple[str, ...]] = []

    async def resoudre(fichiers: tuple[str, ...]) -> None:
        appels.append(fichiers)
        (racine / _FICHIER).write_text("import base\nimport branche\n", encoding="utf-8")

    conflits = await service.rejouer_sur("main", resolveur=resoudre)

    assert appels == [(_FICHIER,)]
    assert conflits == ()
    assert service.raison_resolveur is None
    assert not (racine / ".git" / "rebase-merge").exists()
    contenu = await _git(racine, "show", f"HEAD:{_FICHIER}")
    assert contenu == "import base\nimport branche\n"


async def test_a_file_that_keeps_its_markers_is_still_refused(
    depot: tuple[Path, Path],
) -> None:
    racine, projet = depot
    service = GitWorkspaceService(projet)

    async def resoudre(fichiers: tuple[str, ...]) -> None:
        (racine / _FICHIER).write_text("<<<<<<< HEAD\nimport base\n", encoding="utf-8")

    conflits = await service.rejouer_sur("main", resolveur=resoudre)

    assert conflits == (_FICHIER,)
    assert "marqueurs de conflit restants" in (service.raison_resolveur or "")
    assert not (racine / ".git" / "rebase-merge").exists()


async def test_a_file_missing_from_the_repository_root_is_reported(
    depot: tuple[Path, Path],
) -> None:
    racine, projet = depot
    service = GitWorkspaceService(projet)

    async def resoudre(fichiers: tuple[str, ...]) -> None:
        (racine / _FICHIER).unlink()

    conflits = await service.rejouer_sur("main", resolveur=resoudre)

    assert conflits == (_FICHIER,)
    assert "introuvable" in (service.raison_resolveur or "")
