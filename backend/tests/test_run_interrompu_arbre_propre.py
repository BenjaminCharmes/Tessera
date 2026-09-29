"""After an interrupted run the working tree is clean — ticket-219.

`finish_interrupted` wrote the "INTERROMPU" line into `memory/pipeline-log.md`
**after** `commit_ou_bloquer` had already run `commit_bookkeeping`.  The line
was never committed and the tree stayed dirty.

Fix: every `_log` call in `finish_*` now runs before `commit_ou_bloquer`.

Also covers SQLite WAL files (`*.db-shm`, `*.db-wal`) staged by intent-to-add
during a diff while the backend was running: `_purger_stage_ignoré` removes
them from the index before the commit once they are listed in `.gitignore`.
"""

import asyncio
from datetime import datetime, timezone
from pathlib import Path

import pytest

from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services import pipeline_outcomes as outcomes
from tessera.services.git_workspace import GitWorkspaceService
from tessera.services.pipeline_events import OrchestratorEvent
from tessera.services.pipeline_run import PipelineRun


# ---------------------------------------------------------------------------
# Repo fixture
# ---------------------------------------------------------------------------


async def _git(cwd: Path, *args: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    assert proc.returncode == 0, err.decode()
    return out.decode()


@pytest.fixture
async def repo(tmp_path: Path) -> Path:
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
# Minimal orchestrator stand-in
# ---------------------------------------------------------------------------


class _MockTickets:
    async def update_status(self, ticket_id: str, status: TicketStatus) -> None:
        pass


class _OrchInterrompu:
    """Orchestrateur minimal avec un vrai git et un vrai _log."""

    def __init__(self, projet: Path, git_workspace: GitWorkspaceService) -> None:
        self._git_workspace = git_workspace
        self._ticket_svc = _MockTickets()
        self._max_review_rounds = 3
        self._log_path = projet / "memory" / "pipeline-log.md"

    def _log(self, message: str) -> None:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        line = f"- {ts} — {message}\n"
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        with self._log_path.open("a", encoding="utf-8") as f:
            f.write(line)


def _ticket() -> Ticket:
    return Ticket(
        id="ticket-001",
        title="Un ticket de test",
        type=TicketType.feat,
        status=TicketStatus.in_progress,
        priority=TicketPriority.medium,
        agent="codeur",
        body="",
    )


def _make_run(orch: _OrchInterrompu) -> PipelineRun:
    events: list[OrchestratorEvent] = []

    async def _on_event(event: OrchestratorEvent) -> None:
        events.append(event)

    run = PipelineRun(project_id="projet", ticket=_ticket(), on_event=_on_event)
    run.branch = "ticket-001-un-ticket-de-test"
    run.round_num = 1
    return run


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_run_interrompu_laisse_arbre_propre(repo: Path) -> None:
    """Après un run interrompu par une exception, git status est vide.

    Avant la correction : `_log` écrivait la ligne « INTERROMPU » dans
    `memory/pipeline-log.md` **après** le commit de tenue de livres.  Le
    fichier restait modifié, et `ensure_clean_tree` bloquait le run suivant.
    """
    git = GitWorkspaceService(repo)
    branche = await git.create_branch("ticket-001", "un-ticket-de-test")

    # Travail fictif du codeur
    (repo / "code.py").write_text("x = 1\n", encoding="utf-8")

    orch = _OrchInterrompu(repo, git)
    run = _make_run(orch)
    run.branch = branche

    await outcomes.finish_interrupted(orch, run, RuntimeError("plafond atteint"))

    # Aucun fichier modifié ni non suivi
    proc = await asyncio.create_subprocess_exec(
        "git", "status", "--porcelain",
        cwd=str(repo),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    assert stdout.decode().strip() == "", (
        "l'arbre doit être propre après un run interrompu — "
        f"git status: {stdout.decode().strip()!r}"
    )


async def test_ligne_interrompu_dans_le_dernier_commit(repo: Path) -> None:
    """La ligne « INTERROMPU » figure dans le dernier commit de la branche.

    Avant la correction : `_log` était appelé après `commit_ou_bloquer`, donc
    la ligne était écrite dans le fichier mais n'était jamais commitée.
    """
    git = GitWorkspaceService(repo)
    branche = await git.create_branch("ticket-001", "un-ticket-de-test")

    # Travail fictif du codeur
    (repo / "code.py").write_text("x = 1\n", encoding="utf-8")

    orch = _OrchInterrompu(repo, git)
    run = _make_run(orch)
    run.branch = branche

    await outcomes.finish_interrupted(orch, run, RuntimeError("plafond atteint"))

    # Le dernier commit doit contenir memory/pipeline-log.md avec "INTERROMPU"
    proc = await asyncio.create_subprocess_exec(
        "git", "show", "HEAD:memory/pipeline-log.md",
        cwd=str(repo),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    assert proc.returncode == 0, (
        "memory/pipeline-log.md doit être présent dans le dernier commit"
    )
    content = stdout.decode("utf-8")
    assert "INTERROMPU" in content, (
        f"la ligne INTERROMPU doit figurer dans le dernier commit — contenu : {content!r}"
    )


async def test_fichiers_wal_stagés_non_commités_si_dans_gitignore(repo: Path) -> None:
    """Un WAL stagé avant son entrée dans .gitignore n'entre pas dans le commit.

    `_purger_stage_ignoré` retire ces fichiers de l'index avant que
    `commit_all` ne commite : `git add -A` ne le fait pas seul.
    """
    (repo / ".gitignore").write_text("*.db-shm\n*.db-wal\n", encoding="utf-8")
    await _git(repo, "add", ".gitignore")
    await _git(repo, "commit", "-q", "-m", "chore: ignore sqlite wal")

    # WAL stagé avant que la règle .gitignore n'existe
    wal = repo / "tessera.db-shm"
    wal.write_bytes(b"\x00\x01\x02\x03")
    # -f : c'est l'état d'un fichier indexé avant que la règle existe.
    await _git(repo, "add", "-f", "tessera.db-shm")

    svc = GitWorkspaceService(repo)
    await svc.create_branch("ticket-001", "essai")
    (repo / "code.py").write_text("x = 1\n", encoding="utf-8")

    await svc.commit_all("feat: ticket-001 — essai")

    tracked = await _git(repo, "ls-files")
    assert "tessera.db-shm" not in tracked, (
        "un WAL stagé avant son entrée dans .gitignore ne doit pas être versionné"
    )
