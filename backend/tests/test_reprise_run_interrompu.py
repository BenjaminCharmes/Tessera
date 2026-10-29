"""Recovery of a repository left by a clean stop — ticket-665.

A Ctrl+C is a clean stop: the running runs are written as `interrupted` with a
finish date, so `solder_les_runs_orphelins` never sees them. The recovery at
startup must still put their repository back in order, once.
"""

from __future__ import annotations

from pathlib import Path

from tessera.services.database import create_run, finish_run, init_db
from tessera.services.reprise_orphelin import reprendre_depots_orphelins

from tests.test_reprise_run_orphelin import (
    _git,
    _make_workspace_on_ticket_branch,
    _ticket_frontmatter,
)

_BRANCHE = "ticket-901-mon-ticket"


async def _db_avec_run_interrompu(tmp_path: Path) -> Path:
    """A database holding one run written `interrupted`, as a clean stop does."""
    db = tmp_path / "t.db"
    await init_db(db)
    run_id = await create_run(db, "mon-projet", "ticket-901")
    await finish_run(db, run_id, 1, False, "interrupted")
    return db


async def _poser_fiche_in_progress(repo: Path) -> None:
    """Commit the ticket file under tickets/in-progress/ on the ticket branch."""
    dossier = repo / "tickets" / "in-progress"
    dossier.mkdir(parents=True)
    (dossier / "ticket-901-mon-ticket.md").write_text(
        _ticket_frontmatter("ticket-901", "in-progress"), encoding="utf-8"
    )
    await _git(repo, "add", "tickets")
    await _git(repo, "commit", "-q", "-m", "ticket in progress")
    # Travail du codeur laissé sale par l'arrêt.
    (repo / "README.md").write_text("# projet\n\nmodifié par le codeur\n", encoding="utf-8")


async def test_run_interrompu_sur_branche_ticket_est_repris(tmp_path: Path) -> None:
    """An interrupted run whose repository stayed on the ticket branch is recovered."""
    ws, repo = await _make_workspace_on_ticket_branch(tmp_path)
    await _poser_fiche_in_progress(repo)
    db = await _db_avec_run_interrompu(tmp_path)

    await reprendre_depots_orphelins([], db, ws)

    assert await _git(repo, "rev-parse", "--abbrev-ref", "HEAD") == "develop"
    subject = await _git(repo, "log", "-1", "--pretty=%s", _BRANCHE)
    assert "unapproved work" in subject, subject
    fiche = await _git(repo, "show", f"{_BRANCHE}:tickets/todo/ticket-901-mon-ticket.md")
    assert "status: todo" in fiche, fiche
    fichiers = await _git(repo, "ls-tree", "-r", "--name-only", _BRANCHE)
    assert "tickets/in-progress" not in fichiers, fichiers
    status = await _git(repo, "status", "--porcelain", "--untracked-files=no")
    assert status == "", status


async def test_run_interrompu_deja_sur_la_base_n_est_pas_touche(tmp_path: Path) -> None:
    """An interrupted run whose repository is already on the base branch is left alone."""
    ws, repo = await _make_workspace_on_ticket_branch(tmp_path)
    await _git(repo, "checkout", "-q", "--", "README.md")
    await _git(repo, "checkout", "-q", "develop")
    avant = await _git(repo, "rev-parse", _BRANCHE)
    db = await _db_avec_run_interrompu(tmp_path)

    await reprendre_depots_orphelins([], db, ws)

    assert await _git(repo, "rev-parse", "--abbrev-ref", "HEAD") == "develop"
    assert await _git(repo, "rev-parse", _BRANCHE) == avant


async def test_run_interrompu_n_est_repris_qu_une_fois(tmp_path: Path) -> None:
    """A second startup does not recover the same interrupted run again."""
    ws, repo = await _make_workspace_on_ticket_branch(tmp_path)
    db = await _db_avec_run_interrompu(tmp_path)

    await reprendre_depots_orphelins([], db, ws)
    assert await _git(repo, "rev-parse", "--abbrev-ref", "HEAD") == "develop"
    commits_apres_reprise = await _git(repo, "rev-list", "--count", _BRANCHE)

    # Un humain retourne travailler sur la branche du ticket, sale.
    await _git(repo, "checkout", "-q", _BRANCHE)
    (repo / "README.md").write_text("# projet\n\nretouche à la main\n", encoding="utf-8")

    await reprendre_depots_orphelins([], db, ws)

    assert await _git(repo, "rev-parse", "--abbrev-ref", "HEAD") == _BRANCHE
    assert await _git(repo, "rev-list", "--count", _BRANCHE) == commits_apres_reprise
    assert "README.md" in await _git(repo, "status", "--porcelain")
