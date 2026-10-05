"""Bookkeeping after delivery is never stranded on the ticket branch — ticket-270.

Constat du 2026-09-30 : le commit qui écrit le pr_number dans le ticket était
créé **après** que la PR avait été mergée. Il n'était jamais poussé. Résultat :
le pr_number n'atteignait jamais develop, et des fichiers créés pendant le run
(nouveaux tickets) finissaient dans ce commit orphelin.

Les trois critères :
1. Après une livraison mergée, la branche locale n'a aucun commit absent du distant.
2. Le pr_number d'un ticket livré figure dans le fichier tel qu'il est poussé.
3. Un fichier non suivi au démarrage du run n'entre dans aucun commit de suivi.
"""
import asyncio
from pathlib import Path

import pytest

from tessera.services.git_workspace import GitWorkspaceService
from tessera.services.ticket_service import TicketService


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


def _ticket_md(ticket_id: str, status: str = "done") -> str:
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
# Fixture : dépôt local avec remote nu
# ---------------------------------------------------------------------------


@pytest.fixture
async def repo_with_remote(tmp_path: Path) -> tuple[Path, Path]:
    """Projet local + remote nu — pas de réseau."""
    remote = tmp_path / "remote.git"
    remote.mkdir()
    await _git(remote, "init", "--bare", "-q")

    project = tmp_path / "projet"
    project.mkdir()
    await _git(project, "init", "-q", "-b", "main")
    await _git(project, "config", "user.email", "t@t.local")
    await _git(project, "config", "user.name", "t")
    # Commit initial : une structure de tickets trackée
    tickets_done = project / "tickets" / "done"
    tickets_done.mkdir(parents=True)
    ticket_file = tickets_done / "ticket-001-un-ticket.md"
    ticket_file.write_text(_ticket_md("ticket-001"), encoding="utf-8")
    await _git(project, "add", "tickets")
    await _git(project, "commit", "-q", "-m", "chore: ticket initial")
    await _git(project, "remote", "add", "origin", str(remote))
    await _git(project, "push", "-q", "--set-upstream", "origin", "main")
    return project, remote


@pytest.fixture
async def repo(tmp_path: Path) -> Path:
    """Dépôt local simple — pas de remote."""
    root = tmp_path / "projet"
    root.mkdir()
    await _git(root, "init", "-q", "-b", "main")
    await _git(root, "config", "user.email", "t@t.local")
    await _git(root, "config", "user.name", "t")
    (root / "README.md").write_text("# projet\n", encoding="utf-8")
    await _git(root, "add", "README.md")
    await _git(root, "commit", "-q", "-m", "init")
    return root


# ---------------------------------------------------------------------------
# Critère 1 — Aucun commit local absent du distant après une livraison mergée
# ---------------------------------------------------------------------------


async def test_no_local_only_commits_after_delivery(
    repo_with_remote: tuple[Path, Path],
) -> None:
    """After writing and pushing the pr_number, the local branch matches the remote.

    Simule la séquence réelle : commit principal + commit de suivi pr_number,
    deux pushes. Vérifie qu'aucun commit local n'est absent du distant.
    """
    project, remote = repo_with_remote

    service = GitWorkspaceService(project)
    branch = await service.create_branch("ticket-001", "un-ticket")

    # Le codeur écrit du code
    (project / "feature.py").write_text("x = 1\n", encoding="utf-8")
    await service.commit_all("feat: ticket-001 — un ticket")

    # Premier push (simulant open_pull_request)
    await service.push_branch(branch)

    # Le callback _noter_et_pousser écrit le pr_number, commite, repousse
    ticket_svc = TicketService(project, "proj")
    await ticket_svc.set_pr_number("ticket-001", 42)
    await service.commit_bookkeeping()
    await service.push_branch(branch)  # deuxième push, commit de suivi inclus

    # Aucun commit local ne doit être absent du distant
    ahead = (await _git(project, "rev-list", f"origin/{branch}..{branch}")).strip()
    assert ahead == "", (
        f"commits locaux absents du distant après livraison : {ahead}"
    )


# ---------------------------------------------------------------------------
# Critère 2 — Le pr_number est dans le fichier tel qu'il est poussé
# ---------------------------------------------------------------------------


async def test_pr_number_present_in_pushed_ticket_file(
    repo_with_remote: tuple[Path, Path],
) -> None:
    """The ticket file on the remote branch carries pr_number after the push.

    Vérifie que le pr_number écrit par set_pr_number + commit_bookkeeping +
    push_branch est bien visible sur le distant — pas dans un commit qui ne
    sera jamais poussé.
    """
    project, _remote = repo_with_remote

    service = GitWorkspaceService(project)
    branch = await service.create_branch("ticket-001", "un-ticket")

    # Premier push (simulant open_pull_request)
    (project / "feature.py").write_text("x = 1\n", encoding="utf-8")
    await service.commit_all("feat: ticket-001 — un ticket")
    await service.push_branch(branch)

    # _noter_et_pousser
    ticket_svc = TicketService(project, "proj")
    await ticket_svc.set_pr_number("ticket-001", 99)
    await service.commit_bookkeeping()
    await service.push_branch(branch)

    # Le distant doit contenir le pr_number dans le fichier du ticket
    content = await _git(
        project, "show", f"origin/{branch}:tickets/done/ticket-001-un-ticket.md"
    )
    assert "pr_number: 99" in content, (
        f"pr_number absent du fichier sur le distant : {content!r}"
    )


# ---------------------------------------------------------------------------
# Critère 3 — Un fichier non suivi au démarrage ne rentre pas dans un commit
#             de suivi
# ---------------------------------------------------------------------------


async def test_preexisting_untracked_not_swept_into_bookkeeping(repo: Path) -> None:
    """A file untracked at run start is excluded from commit_bookkeeping.

    Sans le correctif, `git add -A -- tickets/` balayait tous les fichiers
    non suivis dans tickets/, y compris ceux qui existaient avant le run et
    n'ont rien à voir avec le travail du codeur (ticket-270).
    """
    # Crée un dossier tickets/ que git va gérer
    tickets_done = repo / "tickets" / "done"
    tickets_done.mkdir(parents=True)

    # Le fichier du ticket courant — écrit par TicketService pendant le run
    ticket_file = tickets_done / "ticket-001-un-ticket.md"
    ticket_file.write_text(_ticket_md("ticket-001"), encoding="utf-8")

    # Un fichier non suivi qui existait avant le run (scratch, artefact, etc.)
    tickets_todo = repo / "tickets" / "todo"
    tickets_todo.mkdir(parents=True)
    scratch = tickets_todo / "scratch.md"
    scratch.write_text("# brouillon\n", encoding="utf-8")

    service = GitWorkspaceService(repo)
    # Simule l'état enregistré lors de create_branch() au démarrage du run.
    # ticket-001-un-ticket.md était suivi avant le run (déplacement de statut) ;
    # scratch.md existait déjà non suivi (ticket-343).
    service._preexisting_untracked = ("tickets/todo/scratch.md",)
    service._tracked_ticket_basenames = frozenset({"ticket-001-un-ticket.md"})

    await service.commit_bookkeeping()

    # Le commit de suivi doit contenir le fichier du ticket...
    committed = await _git(repo, "show", "--name-only", "--format=", "HEAD")
    assert "ticket-001-un-ticket.md" in committed, (
        f"le fichier ticket manque du commit de suivi : {committed!r}"
    )
    # ...mais PAS le fichier non suivi au démarrage
    assert "scratch.md" not in committed, (
        f"le fichier non suivi au démarrage ne doit pas entrer dans le commit : {committed!r}"
    )
    # Et il doit rester non suivi (pas disparu, pas commité)
    untracked = await _git(repo, "ls-files", "--others", "--exclude-standard")
    assert "tickets/todo/scratch.md" in untracked, (
        "le fichier doit rester non suivi après commit_bookkeeping"
    )
