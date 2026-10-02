"""Rebase abort blocked by untracked Tessera artifacts — ticket-300.

Four tests cover the acceptance criteria:
1. A "modified on base / moved on branch" ticket conflict is auto-resolved.
2. A ``rebase --abort`` blocked by an untracked artifact still leaves the
   tree clean on the original branch.
3. After a failed ``rejouer_sur``, ``.git/rebase-merge`` no longer exists.
4. A conflict on a code file is always aborted and returned (ADR-033).
"""

import asyncio
from pathlib import Path

import pytest

from tessera.services.git_workspace import GitWorkspaceService


async def _git(cwd: Path, *args: str) -> str:
    """Run a git command in *cwd* and return stdout; raise on non-zero."""
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    assert proc.returncode == 0, f"git {' '.join(args)}: {stderr.decode()}"
    return stdout.decode().strip()


@pytest.fixture
async def repo(tmp_path: Path) -> Path:
    """Minimal git repository with a single commit on ``main``."""
    root = tmp_path / "projet"
    root.mkdir()
    await _git(root, "init", "-q", "-b", "main")
    await _git(root, "config", "user.email", "test@tessera.local")
    await _git(root, "config", "user.name", "Tessera test")
    (root / "README.md").write_text("# projet\n", encoding="utf-8")
    await _git(root, "add", "README.md")
    await _git(root, "commit", "-q", "-m", "init")
    return root


# ---------------------------------------------------------------------------
# Test 1 — Ticket moved on branch, modified on base → auto-resolved
# ---------------------------------------------------------------------------


async def test_conflit_ticket_deplace_resolu_automatiquement(repo: Path) -> None:
    """A "modified on base / moved on branch" conflict on a ticket file is resolved.

    Exact scenario from ticket-300: ``develop`` modified a ticket file in
    ``tickets/todo/``; the branch deleted it from ``todo/`` and added it to
    ``tickets/done/``.  ``rejouer_sur`` must succeed, keeping the branch's
    version (file in ``done/``, not in ``todo/``).
    """
    # Setup: create ticket in todo/ and commit on main
    (repo / "tickets" / "todo").mkdir(parents=True)
    (repo / "tickets" / "todo" / "t001.md").write_text("status: todo\n", encoding="utf-8")
    await _git(repo, "add", "tickets")
    await _git(repo, "commit", "-q", "-m", "chore: add ticket")

    # Branch: move ticket to done/ (rename = delete + add)
    await _git(repo, "checkout", "-q", "-b", "ticket-001-x")
    (repo / "tickets" / "done").mkdir(parents=True)
    (repo / "tickets" / "done" / "t001.md").write_text("status: done\n", encoding="utf-8")
    await _git(repo, "rm", "-q", "tickets/todo/t001.md")
    await _git(repo, "add", "tickets/done/t001.md")
    await _git(repo, "commit", "-q", "-m", "chore: ticket done")

    # On main: modify the todo file (simulates bookkeeping on the base branch)
    await _git(repo, "checkout", "-q", "main")
    (repo / "tickets" / "todo" / "t001.md").write_text(
        "status: in-progress\n", encoding="utf-8"
    )
    await _git(repo, "add", "tickets/todo/t001.md")
    await _git(repo, "commit", "-q", "-m", "chore: update ticket status on main")

    # Back on branch: rebase should succeed via auto-resolution
    await _git(repo, "checkout", "-q", "ticket-001-x")
    service = GitWorkspaceService(repo)
    conflits = await service.rejouer_sur("main")

    assert conflits == (), (
        f"Le conflit ticket aurait dû être résolu automatiquement, mais {conflits!r} reste"
    )
    # Branch version wins: done/ exists, todo/ is gone
    assert (repo / "tickets" / "done" / "t001.md").exists(), (
        "tickets/done/t001.md doit exister après résolution en faveur de la branche"
    )
    assert not (repo / "tickets" / "todo" / "t001.md").exists(), (
        "tickets/todo/t001.md ne doit plus exister après résolution"
    )


# ---------------------------------------------------------------------------
# Test 2 — abort blocked by untracked artifact → tree still clean
# ---------------------------------------------------------------------------


async def test_rebase_abort_bloque_par_artefact_laisse_arbre_propre(repo: Path) -> None:
    """An abort blocked by an untracked Tessera artifact still leaves a clean tree.

    ``git rebase --abort`` fails when the original HEAD (before the rebase)
    has a file committed that exists as **untracked** in the current tree:
    git's ``reset --hard <orig-head>`` refuses to overwrite an untracked file.

    Reproduction of the production scenario (ticket-300):
    1. The branch tip commits ``tickets/done/t001.md``.
    2. The rebase resets to main (which has no such file), removing it.
    3. TicketService re-creates the file on disk (simulated here manually).
    4. ``--abort`` tries to restore the branch tip → fails.

    ``_annuler_rebase_robuste`` must detect the blocking artifact, delete it,
    and retry, leaving the tree clean at the original branch position.
    """
    # Main: only code.py — no tickets/ directory
    (repo / "code.py").write_text("x = 1\n", encoding="utf-8")
    await _git(repo, "add", "code.py")
    await _git(repo, "commit", "-q", "-m", "init code")

    # Branch: add tickets/done/t001.md AND change code.py, both in one commit
    await _git(repo, "checkout", "-q", "-b", "ticket-001-x")
    (repo / "tickets" / "done").mkdir(parents=True)
    (repo / "tickets" / "done" / "t001.md").write_text("status: done\n", encoding="utf-8")
    (repo / "code.py").write_text("x = 2\n", encoding="utf-8")
    await _git(repo, "add", ".")
    await _git(repo, "commit", "-q", "-m", "feat: branch change")
    sha_branche = await _git(repo, "rev-parse", "HEAD")
    # sha_branche HAS tickets/done/t001.md committed; main does NOT

    # Main: conflicting code.py change (no tickets/ at all)
    await _git(repo, "checkout", "-q", "main")
    (repo / "code.py").write_text("x = 99\n", encoding="utf-8")
    await _git(repo, "add", "code.py")
    await _git(repo, "commit", "-q", "-m", "feat: main change")

    await _git(repo, "checkout", "-q", "ticket-001-x")

    # Manually trigger the rebase so it pauses on the code.py conflict.
    # git applies the clean addition of tickets/done/t001.md to the index,
    # then stops on code.py (conflict).
    proc = await asyncio.create_subprocess_exec(
        "git", "rebase", "main",
        cwd=str(repo),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await proc.communicate()
    # We are now mid-rebase, paused on code.py conflict.
    # tickets/done/t001.md is staged (clean addition from the cherry-pick).

    # Simulate the scenario where TicketService wrote the file to disk and
    # something else removed it from the index — making it UNTRACKED.
    # This is what caused the production bug: the file was on disk but not in
    # the index, while sha_branche (orig-head) still has it committed.
    # Remove from index only (keep file on disk → untracked).
    proc2 = await asyncio.create_subprocess_exec(
        "git", "rm", "--cached", "--force", "tickets/done/t001.md",
        cwd=str(repo),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await proc2.communicate()
    # Write DIFFERENT content so git cannot skip the overwrite check.
    (repo / "tickets" / "done" / "t001.md").write_text(
        "modified by pipeline\n", encoding="utf-8"
    )
    # tickets/done/t001.md is now UNTRACKED with different content.
    # sha_branche has it committed as "status: done" → plain ``--abort`` fails.

    # _annuler_rebase_robuste must handle the failure and clean up.
    service = GitWorkspaceService(repo)
    await service._annuler_rebase_robuste(sha_branche)

    # Tree is clean: no mid-rebase state
    git_dir = repo / ".git"
    assert not (git_dir / "rebase-merge").exists(), ".git/rebase-merge ne doit pas exister"
    assert not (git_dir / "rebase-apply").exists(), ".git/rebase-apply ne doit pas exister"

    # HEAD is back on the branch
    head_sha = await _git(repo, "rev-parse", "HEAD")
    assert head_sha == sha_branche, (
        f"HEAD doit être revenu sur la branche : {head_sha!r} != {sha_branche!r}"
    )


# ---------------------------------------------------------------------------
# Test 3 — after a failed rejouer_sur, .git/rebase-merge does not exist
# ---------------------------------------------------------------------------


async def test_rejoyer_sur_ne_laisse_pas_rebase_merge_apres_echec(repo: Path) -> None:
    """After ``rejouer_sur`` returns conflicts, ``.git/rebase-merge`` is absent.

    ADR-033: the tree must never stay at mid-rebase.  The next ticket would
    start on a broken state and be immediately blocked.
    """
    # Create a conflict on a code file
    (repo / "app.py").write_text("v = 1\n", encoding="utf-8")
    await _git(repo, "add", "app.py")
    await _git(repo, "commit", "-q", "-m", "init app")

    await _git(repo, "checkout", "-q", "-b", "ticket-002-x")
    (repo / "app.py").write_text("v = 10\n", encoding="utf-8")
    await _git(repo, "add", "app.py")
    await _git(repo, "commit", "-q", "-m", "feat: branch value")

    await _git(repo, "checkout", "-q", "main")
    (repo / "app.py").write_text("v = 20\n", encoding="utf-8")
    await _git(repo, "add", "app.py")
    await _git(repo, "commit", "-q", "-m", "feat: main value")

    await _git(repo, "checkout", "-q", "ticket-002-x")

    service = GitWorkspaceService(repo)
    conflits = await service.rejouer_sur("main")

    assert conflits  # there is a conflict
    git_dir = repo / ".git"
    assert not (git_dir / "rebase-merge").exists(), (
        ".git/rebase-merge doit avoir été supprimé après l'échec de rejouer_sur"
    )
    assert not (git_dir / "rebase-apply").exists(), (
        ".git/rebase-apply doit avoir été supprimé après l'échec de rejouer_sur"
    )


# ---------------------------------------------------------------------------
# Test 4 — code file conflict is always aborted and returned (ADR-033)
# ---------------------------------------------------------------------------


async def test_conflit_fichier_code_annule_et_remonte(repo: Path) -> None:
    """A conflict on a code file is never auto-resolved; it is aborted and returned.

    ADR-033: only ``resolveur-conflit`` (an agent) may resolve code conflicts,
    and always under human review.  ``rejouer_sur`` without a resolver must
    return the conflict files and leave the tree clean.
    """
    (repo / "service.py").write_text("class S: pass\n", encoding="utf-8")
    await _git(repo, "add", "service.py")
    await _git(repo, "commit", "-q", "-m", "init service")

    await _git(repo, "checkout", "-q", "-b", "ticket-003-x")
    sha_branche = await _git(repo, "rev-parse", "HEAD")
    (repo / "service.py").write_text("class S:\n    def run(self): pass\n", encoding="utf-8")
    await _git(repo, "add", "service.py")
    await _git(repo, "commit", "-q", "-m", "feat: add run method")
    sha_branche_apres = await _git(repo, "rev-parse", "HEAD")

    await _git(repo, "checkout", "-q", "main")
    (repo / "service.py").write_text("class Service: pass\n", encoding="utf-8")
    await _git(repo, "add", "service.py")
    await _git(repo, "commit", "-q", "-m", "refactor: rename class")

    await _git(repo, "checkout", "-q", "ticket-003-x")

    service = GitWorkspaceService(repo)
    conflits = await service.rejouer_sur("main")

    # Conflict on code file is returned, not auto-resolved
    assert "service.py" in conflits, (
        f"service.py doit figurer dans les conflits non résolus : {conflits}"
    )

    # Tree is clean — no mid-rebase state
    git_dir = repo / ".git"
    assert not (git_dir / "rebase-merge").exists()

    # HEAD is on the branch (pre-rebase position)
    head = await _git(repo, "rev-parse", "HEAD")
    assert head == sha_branche_apres, (
        f"HEAD doit rester sur la branche après l'annulation : {head!r} != {sha_branche_apres!r}"
    )
