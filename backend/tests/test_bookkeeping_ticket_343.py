"""Bookkeeping commit must not sweep ticket files created during the run — ticket-343.

Three acceptance criteria:
1. A tracked ticket moved from tickets/todo/ to tickets/done/ appears in the
   bookkeeping commit at its new path.
2. A file tickets/todo/ticket-999-x.md created *after* create_branch is not
   staged and remains untracked in the working tree.
3. A file already untracked when create_branch runs stays out of the bookkeeping
   commit (pre-existing untracked behaviour preserved).
"""
import asyncio
from pathlib import Path

import pytest

from tessera.services.git_workspace import GitWorkspaceService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _git(cwd: Path, *args: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "git", *args, cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    assert proc.returncode == 0, err.decode()
    return out.decode()


def _ticket_md(ticket_id: str, status: str = "todo") -> str:
    return (
        f"---\n"
        f"id: {ticket_id}\n"
        f'title: "Un ticket"\n'
        f"type: feat\n"
        f"status: {status}\n"
        f"priority: medium\n"
        f"agent: codeur\n"
        f"---\n\n# {ticket_id}\n"
    )


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
async def repo(tmp_path: Path) -> Path:
    """Local git repo with a tracked ticket in tickets/todo/."""
    root = tmp_path / "projet"
    root.mkdir()
    await _git(root, "init", "-q", "-b", "main")
    await _git(root, "config", "user.email", "t@t.local")
    await _git(root, "config", "user.name", "t")

    todo = root / "tickets" / "todo"
    todo.mkdir(parents=True)
    ticket = todo / "ticket-001-un-ticket.md"
    ticket.write_text(_ticket_md("ticket-001", "todo"), encoding="utf-8")
    await _git(root, "add", "tickets")
    await _git(root, "commit", "-q", "-m", "chore: ticket initial")
    return root


# ---------------------------------------------------------------------------
# Critère 1 — Un ticket suivi déplacé figure dans le commit de suivi
# ---------------------------------------------------------------------------


async def test_moved_ticket_staged_in_bookkeeping(repo: Path) -> None:
    """A tracked ticket moved to another status folder is committed at its new path."""
    service = GitWorkspaceService(repo)
    await service.create_branch("ticket-001", "un-ticket")
    # _tracked_ticket_basenames must include "ticket-001-un-ticket.md"

    # Simulate TicketService moving the ticket from todo/ to done/
    src = repo / "tickets" / "todo" / "ticket-001-un-ticket.md"
    done = repo / "tickets" / "done"
    done.mkdir(parents=True)
    dst = done / "ticket-001-un-ticket.md"
    src.rename(dst)
    dst.write_text(_ticket_md("ticket-001", "done"), encoding="utf-8")

    await service.commit_bookkeeping()

    # --name-status shows renames as "R<score>\told-path\tnew-path",
    # and plain deletes/adds as "D\tpath" / "A\tpath" — both forms contain
    # the new path and a reference to the old path.
    name_status = await _git(repo, "show", "--name-status", "--format=", "HEAD")
    assert "tickets/done/ticket-001-un-ticket.md" in name_status, (
        f"le ticket déplacé doit figurer dans le commit de suivi : {name_status!r}"
    )
    assert "tickets/todo/ticket-001-un-ticket.md" in name_status, (
        f"la suppression de l'ancienne entrée doit figurer dans le commit : {name_status!r}"
    )


# ---------------------------------------------------------------------------
# Critère 2 — Un fichier créé après create_branch ne part pas dans le commit
# ---------------------------------------------------------------------------


async def test_new_ticket_created_during_run_excluded_from_bookkeeping(
    repo: Path,
) -> None:
    """A ticket file created after create_branch is not staged and stays untracked."""
    service = GitWorkspaceService(repo)
    await service.create_branch("ticket-001", "un-ticket")

    # A new ticket written by the user in the IDE while the run is in progress
    new_ticket = repo / "tickets" / "todo" / "ticket-999-a-new-ticket.md"
    new_ticket.write_text(_ticket_md("ticket-999", "todo"), encoding="utf-8")

    await service.commit_bookkeeping()

    # Must not appear in the bookkeeping commit
    committed = await _git(repo, "show", "--name-only", "--format=", "HEAD")
    assert "ticket-999-a-new-ticket.md" not in committed, (
        f"un ticket créé pendant le run ne doit pas entrer dans le commit de suivi : {committed!r}"
    )

    # Must still exist, untracked, in the working tree
    untracked = await _git(
        repo, "ls-files", "--others", "--exclude-standard", "--", "tickets/"
    )
    assert "tickets/todo/ticket-999-a-new-ticket.md" in untracked, (
        "le fichier créé pendant le run doit rester non suivi dans l'arbre"
    )


# ---------------------------------------------------------------------------
# Critère 3 — Un fichier non suivi au démarrage reste exclu (preexisting)
# ---------------------------------------------------------------------------


async def test_preexisting_untracked_excluded_after_create_branch(repo: Path) -> None:
    """A file already untracked when create_branch runs is not staged by bookkeeping."""
    # Add a scratch file that already exists before the run starts
    scratch = repo / "tickets" / "todo" / "scratch.md"
    scratch.write_text("# brouillon\n", encoding="utf-8")

    service = GitWorkspaceService(repo)
    # create_branch records scratch.md in _preexisting_untracked
    await service.create_branch("ticket-001", "un-ticket")

    assert "tickets/todo/scratch.md" in service._preexisting_untracked, (
        "create_branch devrait enregistrer les fichiers non suivis existants"
    )

    await service.commit_bookkeeping()

    # scratch.md must not appear in any commit introduced by commit_bookkeeping
    untracked = await _git(
        repo, "ls-files", "--others", "--exclude-standard", "--", "tickets/"
    )
    assert "tickets/todo/scratch.md" in untracked, (
        "le fichier préexistant non suivi doit rester non suivi après commit_bookkeeping"
    )
