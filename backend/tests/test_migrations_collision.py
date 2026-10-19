"""Colliding Prisma migration numbers are renumbered after the rebase — ticket-484."""
import asyncio
import logging
from pathlib import Path

import pytest

from tessera.services.git_workspace import GitWorkspaceService

_MIG = "prisma/migrations"


async def _git(cwd: Path, *args: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    assert proc.returncode == 0, err.decode()
    return out.decode().strip()


@pytest.fixture
async def repo(tmp_path: Path) -> Path:
    root = tmp_path / "projet"
    root.mkdir()
    await _git(root, "init", "-q")
    await _git(root, "config", "user.email", "test@tessera.local")
    await _git(root, "config", "user.name", "Tessera test")
    (root / "README.md").write_text("v0\n", encoding="utf-8")
    await _git(root, "add", ".")
    await _git(root, "commit", "-q", "-m", "init")
    return root


async def _migration(repo: Path, nom: str, message: str) -> None:
    dossier = repo / _MIG / nom
    dossier.mkdir(parents=True)
    (dossier / "migration.sql").write_text(f"-- {nom}\n", encoding="utf-8")
    await _git(repo, "add", ".")
    await _git(repo, "commit", "-q", "-m", message)


async def _brancher(repo: Path, ticket: str, base_avance: str | None) -> str:
    """A ticket branch holding migration `ticket`; the base gets `base_avance`."""
    base = await _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    await _git(repo, "checkout", "-q", "-b", "ticket-010-migration")
    await _migration(repo, ticket, "feat: ticket-010")
    await _git(repo, "checkout", "-q", base)
    if base_avance is not None:
        await _migration(repo, base_avance, "feat: ticket-009")
    await _git(repo, "checkout", "-q", "ticket-010-migration")
    return base


async def _compte(repo: Path) -> int:
    return int(await _git(repo, "rev-list", "--count", "HEAD"))


async def test_colliding_migration_is_renumbered_and_logged(
    repo: Path, caplog: pytest.LogCaptureFixture
) -> None:
    base = await _brancher(repo, "0005_x", "0005_y")
    service = GitWorkspaceService(repo)

    with caplog.at_level(logging.INFO, logger="tessera.services.git_workspace"):
        conflits = await service.rejouer_sur(base)

    assert conflits == ()
    assert (repo / _MIG / "0006_x" / "migration.sql").read_text(encoding="utf-8") == "-- 0005_x\n"
    assert not (repo / _MIG / "0005_x").exists()
    assert (repo / _MIG / "0005_y" / "migration.sql").is_file()
    lignes = [r for r in caplog.records if r.getMessage() == "migration_renumerotee"]
    assert [(getattr(r, "ancien"), getattr(r, "nouveau")) for r in lignes] == [
        (f"{_MIG}/0005_x", f"{_MIG}/0006_x")
    ]
    assert service.migrations_renumerotees == ((f"{_MIG}/0005_x", f"{_MIG}/0006_x"),)
    assert await _git(repo, "log", "-1", "--format=%s") == (
        "chore: renumber migration 0005_x to 0006_x"
    )
    assert await _git(repo, "status", "--porcelain") == ""


async def test_the_rename_is_a_git_rename_in_its_own_commit(repo: Path) -> None:
    base = await _brancher(repo, "0005_x", "0005_y")

    await GitWorkspaceService(repo).rejouer_sur(base)

    fichiers = await _git(repo, "show", "--name-status", "--format=", "-M", "HEAD")
    assert fichiers.startswith("R100")


@pytest.mark.parametrize(
    ("ticket", "base_avance"),
    [("0006_x", "0005_y"), ("0005_x", None), ("20261015093000_x", "20261015093000_y")],
)
async def test_no_collision_means_no_rename_and_no_commit(
    repo: Path, ticket: str, base_avance: str | None
) -> None:
    base = await _brancher(repo, ticket, base_avance)
    service = GitWorkspaceService(repo)

    conflits = await service.rejouer_sur(base)

    assert conflits == ()
    assert (repo / _MIG / ticket).is_dir()
    assert service.migrations_renumerotees == ()
    # Le ticket a un commit, rejoué sur la base : rien n'est venu s'y ajouter.
    assert await _git(repo, "log", "-1", "--format=%s") == "feat: ticket-010"
    assert await _compte(repo) == 2 + (base_avance is not None)


async def test_a_second_rebase_forgets_the_previous_renames(repo: Path) -> None:
    base = await _brancher(repo, "0005_x", "0005_y")
    service = GitWorkspaceService(repo)
    await service.rejouer_sur(base)
    assert service.migrations_renumerotees

    await service.rejouer_sur(base)

    assert service.migrations_renumerotees == ()


async def test_renumbering_works_in_a_project_nested_in_its_repository(
    tmp_path: Path,
) -> None:
    depot = tmp_path / "depot"
    projet = depot / "projects" / "p"
    projet.mkdir(parents=True)
    await _git(depot, "init", "-q")
    await _git(depot, "config", "user.email", "test@tessera.local")
    await _git(depot, "config", "user.name", "Tessera test")
    (projet / "agents.json").write_text('{"git_root": "ancestor"}\n', encoding="utf-8")
    (depot / "ailleurs" / _MIG / "0005_z").mkdir(parents=True)
    (depot / "ailleurs" / _MIG / "0005_z" / "migration.sql").write_text("--\n", encoding="utf-8")
    await _git(depot, "add", ".")
    await _git(depot, "commit", "-q", "-m", "init")
    base = await _brancher(projet, "0005_x", "0005_y")

    await GitWorkspaceService(projet).rejouer_sur(base)

    assert (projet / _MIG / "0006_x").is_dir()
    assert (depot / "ailleurs" / _MIG / "0005_z").is_dir()
