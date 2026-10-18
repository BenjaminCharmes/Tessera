"""A blocked ticket delivered by hand moves to `done` at the next run — ticket-482.

Real git repository and real `TicketService` on `tmp_path`: the move has to
reach the run's branch, not the base. Only the GitHub lookup is a stand-in.
"""
import asyncio
from pathlib import Path

import httpx
import pytest
import respx

from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services import pipeline_stages as stages
from tessera.services.git_workspace import GitWorkspaceService
from tessera.services.github_service import GitHubService
from tessera.services.github_workflow import GitHubWorkflowService
from tessera.services.pipeline_events import OrchestratorEvent
from tessera.services.pipeline_run import PipelineRun
from tessera.services.ticket_service import TicketService

_JOURNAL = "memory/pipeline-log.md"


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


def _ticket_md(ticket_id: str) -> str:
    return (
        "---\n"
        f"id: {ticket_id}\n"
        'title: "Un ticket"\n'
        "type: feat\n"
        "status: blocked\n"
        "priority: medium\n"
        "agent: codeur\n"
        "---\n\n"
        f"# {ticket_id}\n"
    )


class _Orch:
    """Orchestrator stand-in holding what the start stages read."""

    def __init__(
        self,
        workspace: GitWorkspaceService,
        racine: Path,
        pr_par_prefixe: dict[str, int | Exception],
    ) -> None:
        self._git_workspace = workspace
        self._project_path = racine
        self._base_branch = "develop"
        self._ticket_svc = TicketService(racine, "projet")
        self._pr_par_prefixe = pr_par_prefixe
        self.prefixes_cherches: list[str] = []
        self.logs: list[str] = []

    async def _pr_mergee_de_branche(self, prefix: str) -> int | None:
        self.prefixes_cherches.append(prefix)
        trouve = self._pr_par_prefixe.get(prefix)
        if isinstance(trouve, Exception):
            raise trouve
        return trouve

    async def _sur_la_base(self) -> bool:
        return await self._git_workspace.branche_courante() == self._base_branch

    def _log(self, message: str) -> None:
        self.logs.append(message)


def _run() -> PipelineRun:
    async def _on_event(event: OrchestratorEvent) -> None:
        pass

    ticket = Ticket(
        id="ticket-002", title="Suite", type=TicketType.feat,
        status=TicketStatus.todo, priority=TicketPriority.medium,
        agent="codeur", body="",
    )
    return PipelineRun(project_id="projet", ticket=ticket, on_event=_on_event)


@pytest.fixture
async def projet(tmp_path: Path) -> Path:
    """Project on `develop`, remote in sync, tickets 001 and 003 blocked."""
    bare = tmp_path / "remote.git"
    bare.mkdir()
    await _git(bare, "init", "--bare", "-q")
    local = tmp_path / "local"
    local.mkdir()
    await _git(local, "init", "-q")
    await _git(local, "config", "user.email", "test@tessera.local")
    await _git(local, "config", "user.name", "Tessera test")
    (local / "memory").mkdir()
    (local / _JOURNAL).write_text("- ligne 1\n", encoding="utf-8")
    bloques = local / "tickets" / "blocked"
    bloques.mkdir(parents=True)
    for numero in ("001", "003"):
        (bloques / f"ticket-{numero}-un-ticket.md").write_text(
            _ticket_md(f"ticket-{numero}"), encoding="utf-8"
        )
    await _git(local, "add", "memory", "tickets")
    await _git(local, "commit", "-q", "-m", "init")
    await _git(local, "branch", "-M", "develop")
    await _git(local, "remote", "add", "origin", str(bare))
    await _git(local, "push", "-q", "--set-upstream", "origin", "develop")
    return local


async def _demarrer(
    local: Path, pr_par_prefixe: dict[str, int | Exception]
) -> tuple[_Orch, PipelineRun]:
    orch = _Orch(GitWorkspaceService(local), local, pr_par_prefixe)
    run = _run()
    refused = await stages.create_branch(orch, run)  # type: ignore[arg-type]
    assert refused is None
    return orch, run


async def test_a_blocked_ticket_with_a_merged_pr_moves_to_done_with_its_pr(
    projet: Path,
) -> None:
    await _demarrer(projet, {"ticket-001-": 35})

    assert not (projet / "tickets" / "blocked" / "ticket-001-un-ticket.md").exists()
    ticket = await TicketService(projet, "projet").get_ticket("ticket-001")
    assert ticket is not None
    assert ticket.status is TicketStatus.done
    assert ticket.pr_number == 35
    fichier = projet / "tickets" / "done" / "ticket-001-un-ticket.md"
    assert "status: done" in fichier.read_text(encoding="utf-8")


async def test_a_blocked_ticket_without_a_merged_pr_stays_blocked(
    projet: Path,
) -> None:
    await _demarrer(projet, {"ticket-001-": 35})

    assert (projet / "tickets" / "blocked" / "ticket-003-un-ticket.md").exists()
    ticket = await TicketService(projet, "projet").get_ticket("ticket-003")
    assert ticket is not None
    assert ticket.status is TicketStatus.blocked


async def test_the_putaway_is_logged(projet: Path) -> None:
    orch, run = await _demarrer(projet, {"ticket-001-": 35})

    assert "ticket-001 rangé en done : PR #35 mergée" in orch.logs
    assert not any("ticket-003 rangé" in ligne for ligne in orch.logs)
    assert run.branch is not None


async def test_the_search_prefix_ends_with_a_dash_and_skips_the_running_ticket(
    projet: Path,
) -> None:
    orch, _run_ = await _demarrer(projet, {})

    assert sorted(orch.prefixes_cherches) == ["ticket-001-", "ticket-003-"]


async def test_a_github_error_leaves_the_ticket_blocked_and_the_run_going(
    projet: Path,
) -> None:
    orch, run = await _demarrer(
        projet, {"ticket-001-": RuntimeError("503"), "ticket-003-": 40}
    )

    assert run.branch is not None
    assert (projet / "tickets" / "blocked" / "ticket-001-un-ticket.md").exists()
    # L'erreur sur un ticket n'empêche pas de ranger le suivant.
    assert (projet / "tickets" / "done" / "ticket-003-un-ticket.md").exists()
    assert "ticket-003 rangé en done : PR #40 mergée" in orch.logs


async def test_the_move_follows_the_run_branch_and_leaves_the_base_alone(
    projet: Path,
) -> None:
    avant = await _git(projet, "rev-parse", "develop")

    _orch, run = await _demarrer(projet, {"ticket-001-": 35})

    assert await _git(projet, "branch", "--show-current") == run.branch
    assert await _git(projet, "rev-parse", "develop") == avant
    statut = await _git(projet, "status", "--porcelain", "tickets")
    assert "ticket-001" in statut


# ---------------------------------------------------------------------------
# Recherche de la PR mergée côté GitHub
# ---------------------------------------------------------------------------

_API = "https://api.github.com"
_REPO = "owner/my-repo"


def _pr(
    numero: int, branche: str, mergee: bool, base: str = "develop"
) -> dict[str, object]:
    return {
        "number": numero,
        "merged_at": "2026-10-16T10:00:00Z" if mergee else None,
        "head": {"ref": branche},
        "base": {"ref": base},
    }


@respx.mock
async def test_find_merged_pull_request_returns_the_merged_pr_of_the_prefix() -> None:
    route = respx.get(f"{_API}/repos/{_REPO}/pulls").mock(
        return_value=httpx.Response(200, json=[
            _pr(36, "ticket-017-autre", mergee=True),
            _pr(35, "ticket-001-un-ticket", mergee=True),
        ])
    )

    numero = await GitHubService(token="t", repo=_REPO).find_merged_pull_request(
        "ticket-001-", "develop"
    )

    assert numero == 35
    assert route.calls.last.request.url.params["state"] == "closed"


@respx.mock
async def test_find_merged_pull_request_ignores_closed_unmerged_pr() -> None:
    respx.get(f"{_API}/repos/{_REPO}/pulls").mock(
        return_value=httpx.Response(200, json=[
            _pr(35, "ticket-001-un-ticket", mergee=False),
        ])
    )

    assert await GitHubService(token="t", repo=_REPO).find_merged_pull_request(
        "ticket-001-"
    ) is None


@respx.mock
async def test_find_merged_pull_request_prefix_with_dash_skips_longer_ids() -> None:
    respx.get(f"{_API}/repos/{_REPO}/pulls").mock(
        return_value=httpx.Response(200, json=[
            _pr(90, "ticket-482-un-ticket", mergee=True),
        ])
    )

    assert await GitHubService(token="t", repo=_REPO).find_merged_pull_request(
        "ticket-48-"
    ) is None


@respx.mock
async def test_find_merged_pull_request_ignores_a_pr_merged_into_another_base() -> None:
    respx.get(f"{_API}/repos/{_REPO}/pulls").mock(
        return_value=httpx.Response(200, json=[
            _pr(35, "ticket-001-un-ticket", mergee=True, base="main"),
        ])
    )

    assert await GitHubService(token="t", repo=_REPO).find_merged_pull_request(
        "ticket-001-", "develop"
    ) is None


async def test_workflow_without_github_finds_no_merged_pr() -> None:
    workflow = GitHubWorkflowService(git_workspace=None, github=None, base_branch="develop")

    assert await workflow.pr_mergee_de_branche("ticket-001-") is None
