"""Recovery of repositories left in an intermediate state after a brutal stop — ticket-369.

`solder_les_runs_orphelins` settles orphan runs in the database but leaves
the project repository as the killed process left it. `reprendre_depots_orphelins`
fills the gap: it commits dirty work, moves the ticket back to todo, and
checks out the base branch.
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

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
    """A ticket in tickets/in-review/ is committed in tickets/todo/ with status: todo.

    Après la reprise, la fiche est dans le commit « unapproved work » de la branche
    du ticket, pas sur la branche de base (ticket-375 : la base n'est plus touchée).
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

    # Fiche du ticket dans in-review/ (non suivie par git pour tester le cas limite)
    in_review = repo / "tickets" / "in-review"
    in_review.mkdir(parents=True)
    ticket_file = in_review / "ticket-901-mon-ticket.md"
    ticket_file.write_text(
        _ticket_frontmatter("ticket-901", "in-review"), encoding="utf-8"
    )

    db, orphelins = await _setup_db_with_orphan(tmp_path)

    await reprendre_depots_orphelins(orphelins, db, ws)

    # La fiche doit apparaître dans le commit sur la branche du ticket (ticket-375).
    shown = await _git(
        repo,
        "show",
        "ticket-901-mon-ticket:tickets/todo/ticket-901-mon-ticket.md",
    )
    assert "status: todo" in shown, (
        f"champ status: todo absent du commit sur la branche ticket : {shown!r}"
    )
    assert not ticket_file.exists(), "la fiche ne doit plus être dans in-review/"


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


async def _make_workspace_with_ticket(
    tmp_path: Path, ticket_status: str = "in-progress"
) -> tuple[Path, Path]:
    """Create a workspace with a tracked ticket file on the ticket branch.

    Le ticket est commité sur la branche du ticket (pas sur develop) :
    c'est le cas réel, où le pipeline a déjà poussé la fiche.
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

    # Fiche suivie par git, commitée sur la branche du ticket
    status_dir = repo / "tickets" / ticket_status
    status_dir.mkdir(parents=True)
    ticket_file = status_dir / "ticket-901-mon-ticket.md"
    ticket_file.write_text(
        _ticket_frontmatter("ticket-901", ticket_status), encoding="utf-8"
    )
    await _git(repo, "add", f"tickets/{ticket_status}/ticket-901-mon-ticket.md")
    await _git(repo, "commit", "-q", "-m", "chore: add ticket")

    # Travail du codeur non commité
    (repo / "README.md").write_text("# projet\n\nmodifié\n", encoding="utf-8")
    return ws, repo


async def test_base_branch_sha_inchange_apres_reprise(tmp_path: Path) -> None:
    """After recovery the base branch HEAD SHA is exactly the same as before."""
    ws, repo = await _make_workspace_with_ticket(tmp_path)
    sha_avant = await _git(repo, "rev-parse", "develop")

    db, orphelins = await _setup_db_with_orphan(tmp_path)
    await reprendre_depots_orphelins(orphelins, db, ws)

    sha_apres = await _git(repo, "rev-parse", "develop")
    assert sha_avant == sha_apres, (
        f"le SHA de la branche de base ne doit pas changer "
        f"(avant: {sha_avant!r}, après: {sha_apres!r})"
    )


async def test_statut_propre_base_avec_ticket_apres_reprise(tmp_path: Path) -> None:
    """Base branch has no uncommitted changes after recovery, even when a ticket is reset."""
    ws, repo = await _make_workspace_with_ticket(tmp_path)

    db, orphelins = await _setup_db_with_orphan(tmp_path)
    await reprendre_depots_orphelins(orphelins, db, ws)

    # HEAD est sur develop après la reprise.
    status = await _git(repo, "status", "--porcelain", "--untracked-files=no")
    assert status.strip() == "", (
        f"l'arbre de la branche de base doit être propre ; git status: {status!r}"
    )


async def test_commit_unapproved_contient_ticket_en_todo(tmp_path: Path) -> None:
    """The unapproved-work commit on the ticket branch holds the ticket in tickets/todo/."""
    ws, repo = await _make_workspace_with_ticket(tmp_path, "in-progress")

    db, orphelins = await _setup_db_with_orphan(tmp_path)
    await reprendre_depots_orphelins(orphelins, db, ws)

    # Le contenu du fichier depuis le commit de la branche du ticket.
    shown = await _git(
        repo,
        "show",
        "ticket-901-mon-ticket:tickets/todo/ticket-901-mon-ticket.md",
    )
    assert "status: todo" in shown, (
        f"champ status: todo absent du commit : {shown!r}"
    )
    # La fiche n'est plus dans in-progress/ dans ce commit.
    files_in_commit = await _git(
        repo, "diff-tree", "--no-commit-id", "-r", "--name-only",
        "ticket-901-mon-ticket",
    )
    assert "tickets/todo/ticket-901-mon-ticket.md" in files_in_commit, (
        f"tickets/todo/ absent du commit : {files_in_commit!r}"
    )


async def test_aucune_divergence_base_apres_reprise(tmp_path: Path) -> None:
    """After recovery the base branch has no commit absent from its simulated upstream."""
    ws = tmp_path / "ws"
    ws.mkdir()
    repo = ws / "mon-projet"
    repo.mkdir()

    # Remote simulé : dépôt nu
    bare = tmp_path / "origin.git"
    bare.mkdir()
    await _git(bare, "init", "-q", "--bare", "-b", "develop")

    await _git(repo, "init", "-q", "-b", "develop")
    await _git(repo, "config", "user.email", "test@tessera.local")
    await _git(repo, "config", "user.name", "Tessera Test")
    (repo / "README.md").write_text("# projet\n", encoding="utf-8")
    await _git(repo, "add", "README.md")
    await _git(repo, "commit", "-q", "-m", "init")
    await _git(repo, "remote", "add", "origin", str(bare))
    await _git(repo, "push", "-u", "origin", "develop")

    # Branche du ticket avec un ticket suivi
    await _git(repo, "checkout", "-b", "ticket-901-mon-ticket")
    in_progress = repo / "tickets" / "in-progress"
    in_progress.mkdir(parents=True)
    ticket_file = in_progress / "ticket-901-mon-ticket.md"
    ticket_file.write_text(
        _ticket_frontmatter("ticket-901", "in-progress"), encoding="utf-8"
    )
    await _git(repo, "add", "tickets/in-progress/ticket-901-mon-ticket.md")
    await _git(repo, "commit", "-q", "-m", "chore: add ticket")
    (repo / "README.md").write_text("# projet\n\nmodifié\n", encoding="utf-8")

    db, orphelins = await _setup_db_with_orphan(tmp_path)
    await reprendre_depots_orphelins(orphelins, db, ws)

    # La branche de base locale ne doit avoir aucun commit absent de son amont.
    divergence = await _git(repo, "log", "--oneline", "origin/develop..develop")
    assert divergence.strip() == "", (
        f"la branche de base a divergé de son amont : {divergence!r}"
    )


async def test_fiche_non_suivie_in_progress_dans_commit(tmp_path: Path) -> None:
    """An untracked ticket file in in-progress/ lands in the recovery commit under todo/.

    Simule le cas réel : la fiche passe de tickets/todo/ (suivie) à
    tickets/in-progress/ (non suivie) au démarrage du run, qui meurt aussitôt.
    La reprise doit la retrouver, la remettre en todo et la commiter sur la
    branche du ticket, même si git ne la connaît pas encore.
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

    # Fiche du ticket dans in-progress/ (non suivie par git — le déplacement
    # depuis todo/ n'a pas encore été commité).
    in_progress = repo / "tickets" / "in-progress"
    in_progress.mkdir(parents=True)
    ticket_file = in_progress / "ticket-901-mon-ticket.md"
    ticket_file.write_text(
        _ticket_frontmatter("ticket-901", "in-progress"), encoding="utf-8"
    )

    db, orphelins = await _setup_db_with_orphan(tmp_path)

    await reprendre_depots_orphelins(orphelins, db, ws)

    # Le commit de la branche du ticket doit contenir la fiche dans todo/.
    shown = await _git(
        repo,
        "show",
        "ticket-901-mon-ticket:tickets/todo/ticket-901-mon-ticket.md",
    )
    assert "status: todo" in shown, (
        f"champ status: todo absent du commit sur la branche ticket : {shown!r}"
    )
    assert not ticket_file.exists(), "la fiche ne doit plus être dans in-progress/"


async def test_fiche_non_suivie_seule_dans_commit(tmp_path: Path) -> None:
    """Only the untracked ticket file enters the recovery commit; other untracked files stay out.

    Lorsque la fiche est dans in-progress/ non suivie et qu'un autre fichier
    non suivi traîne dans l'arbre, seule la fiche (remise en todo/) doit
    apparaître dans le commit de reprise. Aucun fichier étranger ne s'y glisse.
    """
    ws, repo = await _make_workspace_on_ticket_branch(tmp_path)

    # Fiche non suivie dans in-progress/
    in_progress = repo / "tickets" / "in-progress"
    in_progress.mkdir(parents=True)
    ticket_file = in_progress / "ticket-901-mon-ticket.md"
    ticket_file.write_text(
        _ticket_frontmatter("ticket-901", "in-progress"), encoding="utf-8"
    )
    # Autre fichier non suivi qui ne doit pas entrer dans le commit.
    brouillon = repo / "brouillon.txt"
    brouillon.write_text("non suivi\n", encoding="utf-8")

    db, orphelins = await _setup_db_with_orphan(tmp_path)

    await reprendre_depots_orphelins(orphelins, db, ws)

    commits = await _git(
        repo, "show", "--name-only", "--format=", "ticket-901-mon-ticket"
    )
    assert "tickets/todo/ticket-901-mon-ticket.md" in commits, (
        f"la fiche doit être dans le commit : {commits!r}"
    )
    assert "brouillon.txt" not in commits, (
        f"brouillon.txt ne doit pas être dans le commit : {commits!r}"
    )
    assert brouillon.exists(), "brouillon.txt doit encore exister sur le disque"
    assert not ticket_file.exists(), "la fiche ne doit plus être dans in-progress/"


# ---------------------------------------------------------------------------
# Tests ticket-389 — fichiers neufs du codeur + ticket approuvé non livré
# ---------------------------------------------------------------------------


async def _lire_started_at(db: Path) -> datetime:
    """Read started_at from the single run in the DB and return an aware datetime."""
    async with aiosqlite.connect(str(db)) as conn:
        cursor = await conn.execute("SELECT started_at FROM pipeline_runs LIMIT 1")
        row = await cursor.fetchone()
    assert row is not None, "aucun run en base"
    dt = datetime.fromisoformat(str(row[0]))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


async def test_fichier_nouveau_entre_dans_commit(tmp_path: Path) -> None:
    """An untracked file newer than started_at lands in the recovery commit."""
    ws, repo = await _make_workspace_on_ticket_branch(tmp_path)
    db, orphelins = await _setup_db_with_orphan(tmp_path)

    started_at = await _lire_started_at(db)
    nouveau = repo / "nouveau.py"
    nouveau.write_text("# nouveau\n", encoding="utf-8")
    new_mtime = started_at.timestamp() + 1.0
    os.utime(str(nouveau), (new_mtime, new_mtime))

    await reprendre_depots_orphelins(orphelins, db, ws)

    commites = await _git(repo, "show", "--name-only", "--format=", "ticket-901-mon-ticket")
    assert "nouveau.py" in commites, (
        f"nouveau.py doit figurer dans le commit de reprise : {commites!r}"
    )


async def test_fichier_ancien_reste_hors_commit(tmp_path: Path) -> None:
    """An untracked file older than started_at is not included in the recovery commit."""
    ws, repo = await _make_workspace_on_ticket_branch(tmp_path)
    db, orphelins = await _setup_db_with_orphan(tmp_path)

    started_at = await _lire_started_at(db)
    ancien = repo / "ancien.py"
    ancien.write_text("# ancien\n", encoding="utf-8")
    old_mtime = started_at.timestamp() - 1.0
    os.utime(str(ancien), (old_mtime, old_mtime))

    await reprendre_depots_orphelins(orphelins, db, ws)

    commites = await _git(repo, "show", "--name-only", "--format=", "ticket-901-mon-ticket")
    assert "ancien.py" not in commites, (
        f"ancien.py ne doit pas figurer dans le commit de reprise : {commites!r}"
    )
    assert ancien.exists(), "le fichier doit encore exister sur le disque"


async def test_depot_imbrique_recent_exclu_du_commit(tmp_path: Path) -> None:
    """A nested git repository newer than started_at is not included in the recovery commit."""
    ws, repo = await _make_workspace_on_ticket_branch(tmp_path)
    db, orphelins = await _setup_db_with_orphan(tmp_path)

    started_at = await _lire_started_at(db)
    imbrique = repo / "nested-repo"
    imbrique.mkdir()
    await _git(imbrique, "init", "-q")
    await _git(imbrique, "config", "user.email", "test@tessera.local")
    await _git(imbrique, "config", "user.name", "Tessera Test")
    fichier_imbrique = imbrique / "f.txt"
    fichier_imbrique.write_text("x\n", encoding="utf-8")
    await _git(imbrique, "add", "f.txt")
    await _git(imbrique, "commit", "-q", "-m", "init")
    # Fichier dans le dépôt imbriqué, mtime > started_at
    new_mtime = started_at.timestamp() + 1.0
    os.utime(str(fichier_imbrique), (new_mtime, new_mtime))

    await reprendre_depots_orphelins(orphelins, db, ws)

    commites = await _git(repo, "show", "--name-only", "--format=", "ticket-901-mon-ticket")
    assert "nested-repo" not in commites, (
        f"nested-repo ne doit pas figurer dans le commit de reprise : {commites!r}"
    )


async def test_ticket_done_non_remis_en_todo(tmp_path: Path) -> None:
    """A ticket already 'done' on the branch is left done; pipeline log records it."""
    ws, repo = await _make_workspace_with_ticket(tmp_path, "done")
    db, orphelins = await _setup_db_with_orphan(tmp_path)

    await reprendre_depots_orphelins(orphelins, db, ws)

    # La fiche doit rester dans done/ sur la branche du ticket (non déplacée en todo/).
    shown = await _git(
        repo,
        "show",
        "ticket-901-mon-ticket:tickets/done/ticket-901-mon-ticket.md",
    )
    assert "status: done" in shown, (
        f"ticket doit rester done sur la branche ticket : {shown!r}"
    )
    # pipeline-log.md doit mentionner « approuvé mais non livré ».
    log_path = repo / "memory" / "pipeline-log.md"
    assert log_path.exists(), "memory/pipeline-log.md doit exister"
    contenu = log_path.read_text(encoding="utf-8")
    assert "approuvé mais non livré" in contenu, (
        f"'approuvé mais non livré' absent du journal : {contenu!r}"
    )
    assert "ticket-901" in contenu, (
        f"ticket_id absent du journal : {contenu!r}"
    )


async def test_le_demarrage_de_l_app_en_test_ne_solde_ni_ne_reprend_rien() -> None:
    """Starting the app in tests never settles runs nor touches a repository.

    `settings` désigne la vraie base et le vrai dossier des projets : le
    testeur du pipeline lance cette suite pendant un run, que chaque
    `TestClient(app)` soldait puis, avec la reprise, commitait et déplaçait
    de branche (2026-10-07). `conftest.py` neutralise les deux appels du
    `lifespan`.
    """
    import tessera.main

    assert await tessera.main.solder_les_runs_orphelins("inutile") == []
    assert await tessera.main.reprendre_depots_orphelins([], "inutile", Path(".")) is None
    assert tessera.main.solder_les_runs_orphelins is not solder_les_runs_orphelins


async def test_projet_imbrique_fichier_nouveau_hors_du_projet(tmp_path: Path) -> None:
    """git_root: ancestor (ide-core): a file the coder created in the
    repository's backend/, outside the project folder, lands in the recovery
    commit; a neighbour project's nested repository does not."""
    racine = tmp_path / "depot"
    ws = racine / "projects"
    projet = ws / "mon-projet"
    projet.mkdir(parents=True)
    await _git(racine, "init", "-q", "-b", "develop")
    await _git(racine, "config", "user.email", "test@tessera.local")
    await _git(racine, "config", "user.name", "Tessera Test")
    (projet / "CLAUDE.md").write_text("# p\n", encoding="utf-8")
    (racine / "README.md").write_text("# depot\n", encoding="utf-8")
    await _git(racine, "add", "README.md", "projects/mon-projet/CLAUDE.md")
    await _git(racine, "commit", "-q", "-m", "init")
    await _git(racine, "checkout", "-q", "-b", "ticket-901-mon-ticket")

    db, orphelins = await _setup_db_with_orphan(tmp_path)
    started_at = await _lire_started_at(db)
    recent = started_at.timestamp() + 1.0

    (racine / "backend").mkdir()
    nouveau = racine / "backend" / "test_nouveau.py"
    nouveau.write_text("# nouveau\n", encoding="utf-8")
    os.utime(str(nouveau), (recent, recent))

    voisin = ws / "voisin"
    voisin.mkdir()
    await _git(voisin, "init", "-q")
    (voisin / "f.txt").write_text("x\n", encoding="utf-8")
    os.utime(str(voisin / "f.txt"), (recent, recent))

    await reprendre_depots_orphelins(orphelins, db, ws)

    commites = await _git(racine, "show", "--name-only", "--format=", "ticket-901-mon-ticket")
    assert "backend/test_nouveau.py" in commites, commites
    assert "voisin" not in commites, commites
