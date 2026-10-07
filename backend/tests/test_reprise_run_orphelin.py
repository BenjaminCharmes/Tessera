"""Recovery of repositories left in an intermediate state after a brutal stop — ticket-369.

`solder_les_runs_orphelins` settles orphan runs in the database but leaves
the project repository as the killed process left it. `reprendre_depots_orphelins`
fills the gap: it commits dirty work, moves the ticket back to todo, and
checks out the base branch.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from tessera.services.database import (
    create_run,
    init_db,
    solder_les_runs_orphelins,
)
from tessera.services.reprise_orphelin import reprendre_depots_orphelins


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _git(cwd: Path, *args: str) -> str:
    """Run git in `cwd` and return stdout. Asserts success."""
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    assert proc.returncode == 0, (
        f"git {' '.join(args)} failed: {err.decode('utf-8', errors='replace')}"
    )
    return out.decode("utf-8", errors="replace").strip()


def _ticket_frontmatter(ticket_id: str, status: str) -> str:
    """Minimal ticket file with valid frontmatter."""
    return (
        "---\n"
        f"id: {ticket_id}\n"
        "title: Mon ticket de test\n"
        "type: feat\n"
        f"status: {status}\n"
        "priority: medium\n"
        "agent: codeur\n"
        "---\n\n"
        "Corps du ticket.\n"
    )


async def _make_workspace_on_ticket_branch(tmp_path: Path) -> tuple[Path, Path]:
    """Create a workspace with a project on a ticket-901-... branch.

    Returns (workspace_dir, repo_path).
    The repo has a develop branch (initial commit) and a ticket-901-mon-ticket
    branch where the tracked README.md is modified and not yet committed.
    """
    ws = tmp_path / "ws"
    ws.mkdir()
    repo = ws / "mon-projet"
    repo.mkdir()

    await _git(repo, "init", "-q", "-b", "develop")
    await _git(repo, "config", "user.email", "test@tessera.local")
    await _git(repo, "config", "user.name", "Tessera Test")
    (repo / "README.md").write_text("# projet\n", encoding="utf-8")
    await _git(repo, "add", "README.md")
    await _git(repo, "commit", "-q", "-m", "init")
    await _git(repo, "checkout", "-b", "ticket-901-mon-ticket")

    # Travail du codeur, non commité : un fichier suivi modifié.
    (repo / "README.md").write_text("# projet\n\nmodifié par le codeur\n", encoding="utf-8")

    return ws, repo


async def _setup_db_with_orphan(
    tmp_path: Path, project_id: str = "mon-projet", ticket_id: str = "ticket-901"
) -> tuple[Path, list[str]]:
    """Create a DB with one orphan run and settle it. Returns (db_path, run_ids)."""
    db = tmp_path / "t.db"
    await init_db(db)
    run_id = await create_run(db, project_id, ticket_id)
    orphelins = await solder_les_runs_orphelins(db)
    return db, orphelins


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_arbre_propre_apres_reprise(tmp_path: Path) -> None:
    """After recovery the working tree has no tracked modifications."""
    ws, repo = await _make_workspace_on_ticket_branch(tmp_path)
    db, orphelins = await _setup_db_with_orphan(tmp_path)

    await reprendre_depots_orphelins(orphelins, db, ws)

    # Seuls les fichiers suivis comptent (--untracked-files=no), comme is_clean().
    status = await _git(repo, "status", "--porcelain", "--untracked-files=no")
    assert status.strip() == "", (
        f"l'arbre doit être propre après la reprise ; git status: {status!r}"
    )


async def test_commit_unapproved_sur_branche_ticket(tmp_path: Path) -> None:
    """The last commit on the ticket branch carries the unapproved-work message."""
    ws, repo = await _make_workspace_on_ticket_branch(tmp_path)
    db, orphelins = await _setup_db_with_orphan(tmp_path)

    await reprendre_depots_orphelins(orphelins, db, ws)

    # On lit le dernier commit de la branche ticket (pas HEAD qui est sur develop).
    subject = await _git(repo, "log", "-1", "--pretty=%s", "ticket-901-mon-ticket")
    assert "ticket-901" in subject, f"ticket_id absent du message : {subject!r}"
    assert "unapproved work" in subject, f"'unapproved work' absent : {subject!r}"
    assert "run interrupted by a backend stop" in subject, (
        f"raison absente du message : {subject!r}"
    )


async def test_ticket_in_review_revient_en_todo(tmp_path: Path) -> None:
    """A ticket in tickets/in-review/ moves back to tickets/todo/ with status: todo."""
    ws = tmp_path / "ws"
    ws.mkdir()
    repo = ws / "mon-projet"
    repo.mkdir()

    await _git(repo, "init", "-q", "-b", "develop")
    await _git(repo, "config", "user.email", "test@tessera.local")
    await _git(repo, "config", "user.name", "Tessera Test")
    (repo / "README.md").write_text("# projet\n", encoding="utf-8")
    await _git(repo, "add", "README.md")
    await _git(repo, "commit", "-q", "-m", "init")
    await _git(repo, "checkout", "-b", "ticket-901-mon-ticket")

    # Fiche du ticket dans in-review/
    in_review = repo / "tickets" / "in-review"
    in_review.mkdir(parents=True)
    ticket_file = in_review / "ticket-901-mon-ticket.md"
    ticket_file.write_text(
        _ticket_frontmatter("ticket-901", "in-review"), encoding="utf-8"
    )

    db, orphelins = await _setup_db_with_orphan(tmp_path)

    await reprendre_depots_orphelins(orphelins, db, ws)

    todo_dir = repo / "tickets" / "todo"
    expected = todo_dir / "ticket-901-mon-ticket.md"
    assert expected.is_file(), "la fiche doit être dans tickets/todo/"
    assert not ticket_file.exists(), "la fiche ne doit plus être dans in-review/"

    content = expected.read_text(encoding="utf-8")
    assert "status: todo" in content, f"champ status: todo absent : {content!r}"


async def test_retour_sur_branche_de_base(tmp_path: Path) -> None:
    """After recovery the working copy is on the base branch (develop)."""
    ws, repo = await _make_workspace_on_ticket_branch(tmp_path)
    db, orphelins = await _setup_db_with_orphan(tmp_path)

    await reprendre_depots_orphelins(orphelins, db, ws)

    current = await _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    assert current == "develop", f"la branche courante doit être develop, pas {current!r}"


async def test_autre_branche_pas_de_changement(tmp_path: Path) -> None:
    """If the working copy is on a branch other than the ticket's, nothing changes."""
    ws = tmp_path / "ws"
    ws.mkdir()
    repo = ws / "mon-projet"
    repo.mkdir()

    await _git(repo, "init", "-q", "-b", "develop")
    await _git(repo, "config", "user.email", "test@tessera.local")
    await _git(repo, "config", "user.name", "Tessera Test")
    (repo / "README.md").write_text("# projet\n", encoding="utf-8")
    await _git(repo, "add", "README.md")
    await _git(repo, "commit", "-q", "-m", "init")
    await _git(repo, "checkout", "-b", "autre-branche")

    # Nombre de commits avant
    count_before = await _git(repo, "rev-list", "--count", "HEAD")

    db, orphelins = await _setup_db_with_orphan(tmp_path)

    await reprendre_depots_orphelins(orphelins, db, ws)

    # La branche n'a pas changé
    current = await _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    assert current == "autre-branche", f"la branche ne doit pas changer : {current!r}"

    # Aucun commit ajouté
    count_after = await _git(repo, "rev-list", "--count", "HEAD")
    assert count_after == count_before, (
        f"aucun commit ne doit être ajouté (avant: {count_before}, après: {count_after})"
    )


async def test_erreur_git_journalisee_sans_exception(tmp_path: Path) -> None:
    """A git error during recovery is logged but does not raise an exception."""
    ws = tmp_path / "ws"
    ws.mkdir()
    # Dossier de projet sans dépôt git — provoque une erreur git
    bad = ws / "bad-projet"
    bad.mkdir()

    db = tmp_path / "t.db"
    await init_db(db)
    run_id = await create_run(db, "bad-projet", "ticket-901")
    orphelins = await solder_les_runs_orphelins(db)

    # Ne doit pas lever d'exception, quelle que soit l'erreur git
    await reprendre_depots_orphelins(orphelins, db, ws)


async def test_ni_fichier_non_suivi_ni_depot_imbrique_dans_le_commit(tmp_path: Path) -> None:
    """Recovery commits tracked changes only: no untracked file, no nested repository.

    Pour un projet `git_root: ancestor`, le dépôt est celui de Tessera entier :
    un `git add -A` y embarquerait les autres projets de `projects/` (dépôts
    git à part) comme sous-dépôts, et tout fichier non suivi.
    """
    ws, repo = await _make_workspace_on_ticket_branch(tmp_path)
    (repo / "brouillon.txt").write_text("non suivi\n", encoding="utf-8")
    imbrique = repo / "autre-projet"
    imbrique.mkdir()
    # Un vrai projet voisin : un dépôt avec au moins un commit.
    await _git(imbrique, "init", "-q")
    await _git(imbrique, "config", "user.email", "test@tessera.local")
    await _git(imbrique, "config", "user.name", "Tessera Test")
    (imbrique / "f.txt").write_text("x\n", encoding="utf-8")
    await _git(imbrique, "add", "f.txt")
    await _git(imbrique, "commit", "-q", "-m", "init")
    db, orphelins = await _setup_db_with_orphan(tmp_path)

    await reprendre_depots_orphelins(orphelins, db, ws)

    message = await _git(repo, "log", "-1", "--format=%s", "ticket-901-mon-ticket")
    assert "unapproved work" in message
    commites = await _git(repo, "show", "--name-only", "--format=", "ticket-901-mon-ticket")
    assert "README.md" in commites
    assert "brouillon.txt" not in commites
    assert "autre-projet" not in commites
    assert (repo / "brouillon.txt").read_text(encoding="utf-8") == "non suivi\n"
