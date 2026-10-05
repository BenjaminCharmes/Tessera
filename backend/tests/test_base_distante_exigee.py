"""A failed fetch of the base never forks a ticket silently from a stale base — ticket-340.

Démineur, 2026-10-05 : la PR du ticket-033 est mergée à 10:46:59, et la
branche du ticket-034 (`depends_on: ticket-033`) est créée à 10:47:03 depuis
la base d'avant ce merge. Le `git fetch` avait échoué ; `initialiser_base_ref`
s'était rabattu sur la branche locale, périmée, sans dire pourquoi. Le 034,
approuvé, s'est arrêté sur un conflit à la livraison.
"""
import asyncio
import logging
from pathlib import Path

import pytest

from tessera.services import git_workspace as gw
from tessera.services.git_workspace import GitCommandError, GitWorkspaceService
from tessera.services.politique_run import PolitiqueRun


async def _git(cwd: Path, *args: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "git", *args, cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    assert proc.returncode == 0, stderr.decode()
    return stdout.decode().strip()


@pytest.fixture(autouse=True)
def _sans_attente(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gw, "_ATTENTE_ENTRE_FETCH_S", 0.0)


@pytest.fixture
async def depot(tmp_path: Path) -> tuple[Path, str]:
    """A repo whose remote `main` is one commit ahead of the local `main`."""
    bare = tmp_path / "remote.git"
    bare.mkdir()
    await _git(bare, "init", "--bare", "-q")
    local = tmp_path / "local"
    local.mkdir()
    await _git(local, "init", "-q")
    await _git(local, "config", "user.email", "test@tessera.local")
    await _git(local, "config", "user.name", "Tessera test")
    (local / "a.txt").write_text("a\n", encoding="utf-8")
    await _git(local, "add", ".")
    await _git(local, "commit", "-q", "-m", "init")
    await _git(local, "branch", "-M", "main")
    await _git(local, "remote", "add", "origin", str(bare))
    await _git(local, "push", "-q", "-u", "origin", "main")
    # Le merge du ticket précédent, arrivé sur le distant seulement.
    await _git(local, "commit", "-q", "--allow-empty", "-m", "merge of ticket-033")
    distant = await _git(local, "rev-parse", "HEAD")
    await _git(local, "push", "-q", "origin", "main")
    await _git(local, "reset", "-q", "--hard", "HEAD~1")
    return local, distant


def _service(local: Path) -> GitWorkspaceService:
    return GitWorkspaceService(local, politique=PolitiqueRun(base_branch="main"))


def _fetch_en_panne(service: GitWorkspaceService, echecs: int) -> list[int]:
    """Make the first `echecs` fetches fail, like a transient network error."""
    vrai_run = service._run
    appels = [0]

    async def run(*args: str) -> str:
        if args[:1] == ("fetch",):
            appels[0] += 1
            if appels[0] <= echecs:
                raise GitCommandError(["git", *args], 128, "fatal: unable to access")
        return await vrai_run(*args)

    service._run = run  # type: ignore[method-assign]
    return appels


async def test_a_transient_fetch_failure_is_retried(depot: tuple[Path, str]) -> None:
    local, distant = depot
    service = _service(local)
    appels = _fetch_en_panne(service, echecs=1)

    assert await service.initialiser_base_ref() is None
    assert service._base_ref == distant
    assert appels[0] == 2


async def test_a_ticket_with_dependencies_is_blocked_when_the_remote_cannot_be_read(
    depot: tuple[Path, str],
) -> None:
    local, _ = depot
    service = _service(local)
    _fetch_en_panne(service, echecs=99)

    raison = await service.initialiser_base_ref(exiger_distant=True)

    assert raison is not None
    assert "unable to access" in raison
    assert service._base_ref is None


async def test_without_dependencies_the_local_fallback_stays_and_says_why(
    depot: tuple[Path, str], caplog: pytest.LogCaptureFixture,
) -> None:
    local, distant = depot
    service = _service(local)
    _fetch_en_panne(service, echecs=99)

    with caplog.at_level(logging.WARNING, logger="tessera.services.git_workspace"):
        assert await service.initialiser_base_ref() is None

    assert service._base_ref == await _git(local, "rev-parse", "main")
    assert service._base_ref != distant
    assert any("unable to access" in str(getattr(r, "erreur", "")) for r in caplog.records)


class _Tickets:
    def __init__(self) -> None:
        self.statuts: list[object] = []

    async def update_status(self, ticket_id: str, status: object) -> None:
        self.statuts.append(status)


class _Orch:
    def __init__(self, workspace: GitWorkspaceService, racine: Path) -> None:
        self._git_workspace = workspace
        self._ticket_svc = _Tickets()
        self._project_path = racine
        self.logs: list[str] = []

    def _log(self, message: str) -> None:
        self.logs.append(message)


async def test_the_branch_stage_blocks_a_dependent_ticket_without_a_readable_remote(
    depot: tuple[Path, str],
) -> None:
    from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
    from tessera.services import pipeline_stages as stages
    from tessera.services.pipeline_events import OrchestratorEvent
    from tessera.services.pipeline_run import PipelineRun

    local, _ = depot
    await _git(local, "remote", "set-url", "origin", str(local.parent / "disparu.git"))

    async def _on_event(event: OrchestratorEvent) -> None:
        pass

    ticket = Ticket(
        id="ticket-034", title="Niveau personnalisé", type=TicketType.feat,
        status=TicketStatus.todo, priority=TicketPriority.medium, agent="codeur",
        body="", depends_on=["ticket-033"],
    )
    run = PipelineRun(project_id="demineur", ticket=ticket, on_event=_on_event)
    orch = _Orch(_service(local), local)

    result = await stages.create_branch(orch, run)  # type: ignore[arg-type]

    assert result is not None
    assert result.final_status is TicketStatus.blocked
    assert "base distante" in (result.arret or "")
    assert run.branch is None
