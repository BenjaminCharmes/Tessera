"""A failed recovery leaves the interrupted run to recover — ticket-875.

`depot_repris_at` is written only once the repository recovery succeeded: a
failed commit (git lock, hook) must be retried at the next startup, not
forgotten.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import aiosqlite
import pytest

from tessera.services.git_workspace.git_runner import GitResult
from tessera.services.git_workspace.git_runner import git as vrai_git
from tessera.services.noyau.database import init_db
from tessera.services.noyau.database_runs import create_run, finish_run
from tessera.services.pipeline import reprise_orphelin
from tessera.services.pipeline.reprise_orphelin import reprendre_depots_orphelins
from tests.test_reprise_run_orphelin import _git, _make_workspace_on_ticket_branch

_BRANCHE = "ticket-901-mon-ticket"


async def _db_avec_run_interrompu(tmp_path: Path) -> tuple[Path, str]:
    """A database holding one run written `interrupted`, and its id."""
    db = tmp_path / "t.db"
    await init_db(db)
    run_id = await create_run(db, "mon-projet", "ticket-901")
    await finish_run(db, run_id, 1, False, "interrupted")
    return db, run_id


async def _depot_repris_at(db: Path, run_id: str) -> str | None:
    """The `depot_repris_at` column of a run."""
    async with aiosqlite.connect(str(db)) as conn:
        async with conn.execute(
            "SELECT depot_repris_at FROM pipeline_runs WHERE id = ?", (run_id,)
        ) as cursor:
            ligne = await cursor.fetchone()
    assert ligne is not None
    return None if ligne[0] is None else str(ligne[0])


def _git_dont_le_commit_echoue(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the recovery's git by a double whose `commit` fails (git lock)."""

    async def git_double(cwd: Path, *args: str) -> GitResult:
        if args and args[0] == "commit":
            return GitResult(code=128, out="", err="index.lock exists", command=args)
        return await vrai_git(cwd, *args)

    monkeypatch.setattr(reprise_orphelin, "git", git_double)


async def _salir_l_arbre(repo: Path) -> None:
    """Leave tracked work in progress on the ticket branch, as a killed run does."""
    (repo / "README.md").write_text("# projet\n\nmodifié par le codeur\n", encoding="utf-8")
    assert "README.md" in await _git(repo, "status", "--porcelain")


async def test_echec_du_commit_laisse_le_run_a_reprendre(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A recovery whose commit fails leaves `depot_repris_at` null."""
    ws, repo = await _make_workspace_on_ticket_branch(tmp_path)
    await _salir_l_arbre(repo)
    db, run_id = await _db_avec_run_interrompu(tmp_path)
    _git_dont_le_commit_echoue(monkeypatch)

    await reprendre_depots_orphelins([], db, ws)

    assert await _depot_repris_at(db, run_id) is None
    assert await _git(repo, "rev-parse", "--abbrev-ref", "HEAD") == _BRANCHE


async def test_demarrage_suivant_reprend_puis_marque(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """After a failed attempt, the next startup recovers the same run and marks it."""
    ws, repo = await _make_workspace_on_ticket_branch(tmp_path)
    await _salir_l_arbre(repo)
    db, run_id = await _db_avec_run_interrompu(tmp_path)
    _git_dont_le_commit_echoue(monkeypatch)
    await reprendre_depots_orphelins([], db, ws)
    assert await _depot_repris_at(db, run_id) is None

    monkeypatch.setattr(reprise_orphelin, "git", vrai_git)
    await reprendre_depots_orphelins([], db, ws)

    assert await _git(repo, "rev-parse", "--abbrev-ref", "HEAD") == "develop"
    assert "unapproved work" in await _git(repo, "log", "-1", "--pretty=%s", _BRANCHE)
    assert await _depot_repris_at(db, run_id) is not None


async def test_reprise_reussie_pose_depot_repris_at(tmp_path: Path) -> None:
    """A successful recovery marks the run as recovered."""
    ws, repo = await _make_workspace_on_ticket_branch(tmp_path)
    await _salir_l_arbre(repo)
    db, run_id = await _db_avec_run_interrompu(tmp_path)

    await reprendre_depots_orphelins([], db, ws)

    assert await _git(repo, "rev-parse", "--abbrev-ref", "HEAD") == "develop"
    assert await _depot_repris_at(db, run_id) is not None


def test_reprendre_depot_seul_declare_un_retour_bool() -> None:
    """`_reprendre_depot_seul` reports its success as a `bool`."""
    annotation = inspect.signature(reprise_orphelin._reprendre_depot_seul).return_annotation
    assert annotation in (bool, "bool")
