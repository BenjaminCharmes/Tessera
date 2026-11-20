"""A base that only differs in history is realigned; a refused start leaves a clean tree — ticket-970."""
import asyncio
from pathlib import Path

import pytest

from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services.gardes.politique_run import PolitiqueRun
from tessera.services.git_workspace import GitCommandError, GitWorkspaceService
from tessera.services.noyau.pipeline_events import OrchestratorEvent
from tessera.services.pipeline import pipeline_branche
from tessera.services.pipeline.pipeline_run import PipelineRun


async def _git(cwd: Path, *args: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "git", *args, cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    assert proc.returncode == 0, err.decode()
    return out.decode().strip()


async def _identite(depot: Path) -> None:
    await _git(depot, "config", "user.email", "test@tessera.local")
    await _git(depot, "config", "user.name", "Tessera test")


@pytest.fixture
async def depot(tmp_path: Path) -> tuple[Path, Path]:
    """A local `develop` pushed to a bare remote."""
    bare = tmp_path / "remote.git"
    bare.mkdir()
    await _git(bare, "init", "--bare", "-q")
    local = tmp_path / "local"
    local.mkdir()
    await _git(local, "init", "-q")
    await _identite(local)
    (local / "README.md").write_text("# projet\n", encoding="utf-8")
    await _git(local, "add", "README.md")
    await _git(local, "commit", "-q", "-m", "init")
    await _git(local, "branch", "-M", "develop")
    await _git(local, "remote", "add", "origin", str(bare))
    await _git(local, "push", "-q", "-u", "origin", "develop")
    return local, bare


async def _commit_local(local: Path, nom: str, contenu: str, message: str) -> None:
    (local / nom).write_text(contenu, encoding="utf-8")
    await _git(local, "add", nom)
    await _git(local, "commit", "-q", "-m", message)


async def _commit_distant(local: Path, bare: Path, fichiers: dict[str, str]) -> str:
    """Push one commit holding `fichiers` to the remote develop, from another clone."""
    autre = local.parent / "autre"
    await _git(local.parent, "clone", "-q", str(bare), str(autre))
    await _identite(autre)
    await _git(autre, "checkout", "-q", "develop")
    for nom, contenu in fichiers.items():
        (autre / nom).write_text(contenu, encoding="utf-8")
        await _git(autre, "add", nom)
    await _git(autre, "commit", "-q", "-m", "squash")
    await _git(autre, "push", "-q", "origin", "develop")
    return await _git(autre, "rev-parse", "HEAD")


async def _squash_distant(local: Path, bare: Path) -> str:
    """Local develop holds two commits; the remote holds them squashed in one."""
    await _commit_local(local, "a.py", "a\n", "feat: a")
    await _commit_local(local, "b.py", "b\n", "chore: tessera pipeline bookkeeping")
    return await _commit_distant(local, bare, {"a.py": "a\n", "b.py": "b\n"})


async def test_squashed_base_is_realigned_on_the_remote(depot: tuple[Path, Path]) -> None:
    local, bare = depot
    distant = await _squash_distant(local, bare)
    service = GitWorkspaceService(local)

    assert await service.initialiser_base_ref("develop") is None

    assert await _git(local, "rev-parse", "refs/heads/develop") == distant
    assert service._base_ref == distant
    assert await _git(local, "status", "--porcelain") == ""


async def test_realignment_is_journalised(
    depot: tuple[Path, Path], caplog: pytest.LogCaptureFixture
) -> None:
    local, bare = depot
    await _commit_local(local, "a.py", "a\n", "feat: a")
    ancien = await _git(local, "rev-parse", "HEAD")
    distant = await _commit_distant(local, bare, {"a.py": "a\n"})
    caplog.set_level("INFO", logger="tessera.services.git_workspace")

    await GitWorkspaceService(local).initialiser_base_ref("develop")

    ligne = next(r for r in caplog.records if r.getMessage() == "base_realignee")
    assert (ligne.ancien, ligne.nouveau) == (ancien, distant)  # type: ignore[attr-defined]


async def test_different_trees_keep_the_refusal(depot: tuple[Path, Path]) -> None:
    local, bare = depot
    await _commit_local(local, "a.py", "local\n", "feat: a")
    await _commit_distant(local, bare, {"a.py": "distant\n"})
    avant = await _git(local, "rev-parse", "refs/heads/develop")

    raison = await GitWorkspaceService(local).initialiser_base_ref("develop")

    assert raison is not None and "divergé" in raison
    assert await _git(local, "rev-parse", "refs/heads/develop") == avant


async def test_dirty_tree_keeps_the_refusal(depot: tuple[Path, Path]) -> None:
    local, bare = depot
    await _squash_distant(local, bare)
    (local / "README.md").write_text("modifié\n", encoding="utf-8")
    avant = await _git(local, "rev-parse", "refs/heads/develop")

    raison = await GitWorkspaceService(local).initialiser_base_ref("develop")

    assert raison is not None and "divergé" in raison
    assert await _git(local, "rev-parse", "refs/heads/develop") == avant


async def test_checkout_off_the_base_keeps_the_refusal(depot: tuple[Path, Path]) -> None:
    local, bare = depot
    await _squash_distant(local, bare)
    await _git(local, "checkout", "-q", "-b", "ticket-001-autre")
    avant = await _git(local, "rev-parse", "refs/heads/develop")

    raison = await GitWorkspaceService(local).initialiser_base_ref("develop")

    assert raison is not None and "divergé" in raison
    assert await _git(local, "rev-parse", "refs/heads/develop") == avant


async def test_ticket_fetch_between_base_fetch_and_read_does_not_move_the_base(
    depot: tuple[Path, Path],
) -> None:
    """The incident path: a fetch of the ticket branch lands after the base fetch.

    `FETCH_HEAD` then holds the ticket tip; the local base must stay on the remote one.
    """
    local, _ = depot
    await _git(local, "checkout", "-q", "-b", "ticket-001-x")
    await _commit_local(local, "t.py", "t\n", "feat: t")
    await _git(local, "push", "-q", "origin", "ticket-001-x")
    tete_ticket = await _git(local, "rev-parse", "HEAD")
    await _git(local, "checkout", "-q", "develop")
    distant = await _git(local, "rev-parse", "origin/develop")
    service = GitWorkspaceService(local)
    fetch_base = service._fetch_base

    async def fetch_puis_ticket(base_branch: str) -> None:
        await fetch_base(base_branch)
        await service._run("fetch", "origin", "ticket-001-x")

    service._fetch_base = fetch_puis_ticket  # type: ignore[method-assign]

    assert await service.initialiser_base_ref("develop") is None

    assert await _git(local, "rev-parse", "FETCH_HEAD") == tete_ticket
    assert await _git(local, "rev-parse", "refs/heads/develop") == distant
    assert service._base_ref == distant
    assert not (local / "t.py").exists()


class _Tickets:
    def __init__(self) -> None:
        self.statuts: list[TicketStatus] = []

    async def update_status(self, ticket_id: str, status: TicketStatus) -> None:
        self.statuts.append(status)


class _Orch:
    def __init__(self, workspace: GitWorkspaceService, racine: Path) -> None:
        self._git_workspace = workspace
        self._project_path = racine
        self._base_branch = "develop"
        self._ticket_svc = _Tickets()

    def _log(self, message: str) -> None:
        pass


def _run() -> PipelineRun:
    async def _on_event(event: OrchestratorEvent) -> None:
        pass

    ticket = Ticket(
        id="ticket-002", title="Next", type=TicketType.feat, status=TicketStatus.todo,
        priority=TicketPriority.medium, agent="codeur", body="",
    )
    return PipelineRun(project_id="projet", ticket=ticket, on_event=_on_event)


async def test_run_refused_at_start_leaves_a_clean_tree(depot: tuple[Path, Path]) -> None:
    local, bare = depot
    await _commit_local(local, "a.py", "local\n", "feat: a")
    await _commit_distant(local, bare, {"a.py": "distant\n"})
    orch = _Orch(GitWorkspaceService(local, politique=PolitiqueRun(base_branch="develop")), local)

    resultat = await pipeline_branche.create_branch(orch, _run())  # type: ignore[arg-type]

    assert resultat is not None and resultat.final_status is TicketStatus.blocked
    assert await _git(local, "status", "--porcelain") == ""
    assert orch._ticket_svc.statuts == []


async def test_squashed_base_lets_the_run_start(depot: tuple[Path, Path]) -> None:
    local, bare = depot
    distant = await _squash_distant(local, bare)
    orch = _Orch(GitWorkspaceService(local, politique=PolitiqueRun(base_branch="develop")), local)

    resultat = await pipeline_branche.create_branch(orch, _run())  # type: ignore[arg-type]

    assert resultat is None
    assert await _git(local, "rev-parse", "refs/heads/develop") == distant
    assert await _git(local, "branch", "--show-current") == "ticket-002-next"


async def test_failed_branch_creation_leaves_a_clean_tree(depot: tuple[Path, Path]) -> None:
    local, _ = depot
    service = GitWorkspaceService(local)

    async def echec(ticket_id: str, slug: str) -> str:
        raise GitCommandError(["checkout", "-b"], 1, "fatal: échec simulé")

    service.create_branch = echec  # type: ignore[method-assign]
    orch = _Orch(service, local)

    resultat = await pipeline_branche.create_branch(orch, _run())  # type: ignore[arg-type]

    assert resultat is not None and resultat.final_status is TicketStatus.blocked
    assert await _git(local, "status", "--porcelain") == ""
    assert orch._ticket_svc.statuts == []
