"""A refused link ends the run at once, named, with an unapproved commit — ticket-1005."""
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services.git_workspace import GitWorkspaceService
from tessera.services.git_workspace.liens import LienNonDeclare
from tessera.services.noyau.pipeline_events import OrchestratorEvent
from tessera.services.pipeline import pipeline_testeur
from tessera.services.pipeline.pipeline_lien_refuse import finish_lien_refuse
from tessera.services.pipeline.pipeline_production import _capture_diff
from tessera.services.pipeline.pipeline_run import PipelineRun
from tests.depot_worktree import git, lier


@pytest.fixture
def depot(tmp_path: Path) -> Path:
    racine = tmp_path / "projet"
    racine.mkdir()
    git(racine, "init", "-q", "-b", "main")
    git(racine, "config", "user.email", "t@example.com")
    git(racine, "config", "user.name", "T")
    (racine / "README.md").write_text("# p\n", encoding="utf-8")
    git(racine, "add", "README.md")
    git(racine, "commit", "-q", "-m", "init")
    return racine


class _Tickets:
    async def update_status(self, ticket_id: str, status: TicketStatus) -> None:
        pass


class _Orch:
    def __init__(self, projet: Path, workspace: Any) -> None:
        self._git_workspace = workspace
        self._ticket_svc = _Tickets()
        self._project_path = projet
        self._test_runner = AsyncMock()
        self._test_command = None
        self._max_review_rounds = 3
        self.journal: list[str] = []

    def _log(self, message: str) -> None:
        self.journal.append(message)


def _run() -> PipelineRun:
    async def _on_event(event: OrchestratorEvent) -> None:
        pass

    ticket = Ticket(
        id="ticket-001", title="t", type=TicketType.feat, status=TicketStatus.in_progress,
        priority=TicketPriority.medium, agent="codeur", body="",
    )
    run = PipelineRun(project_id="projet", ticket=ticket, on_event=_on_event)
    run.round_num = 1
    return run


def _cible(depot: Path) -> Path:
    dehors = depot.parent / "dehors"
    dehors.mkdir()
    (dehors / "secret.txt").write_text("ne pas indexer", encoding="utf-8")
    return dehors


async def _preparer(depot: Path) -> tuple[_Orch, PipelineRun, Path]:
    workspace = GitWorkspaceService(depot)
    run = _run()
    run.branch = await workspace.create_branch("ticket-001", "t")
    cible = _cible(depot)
    (depot / "travail.txt").write_text("ok", encoding="utf-8")
    lier(cible, depot / "lien")
    return _Orch(depot, workspace), run, cible


async def test_a_refused_link_blocks_the_run_and_names_the_link(depot: Path) -> None:
    orch, run, _ = await _preparer(depot)

    with pytest.raises(LienNonDeclare) as lu:
        await _capture_diff(orch, run, "prose du codeur")  # type: ignore[arg-type]
    resultat = await finish_lien_refuse(orch, run, lu.value)  # type: ignore[arg-type]

    assert resultat.final_status is TicketStatus.blocked
    assert resultat.approved is False
    assert "lien" in (resultat.arret or "")


async def test_the_work_is_committed_without_the_link_target(depot: Path) -> None:
    orch, run, cible = await _preparer(depot)

    await finish_lien_refuse(orch, run, LienNonDeclare(["lien"]))  # type: ignore[arg-type]

    assert "unapproved work" in git(depot, "log", "-1", "--format=%s")
    fichiers = git(depot, "ls-tree", "-r", "--name-only", "HEAD")
    assert "travail.txt" in fichiers
    assert "secret.txt" not in fichiers
    assert (cible / "secret.txt").read_text(encoding="utf-8") == "ne pas indexer"
    assert not (depot / "lien").exists()
    assert git(depot, "status", "--porcelain") == ""


async def test_a_link_that_cannot_be_removed_is_named_and_nothing_is_committed(
    depot: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    orch, run, _ = await _preparer(depot)
    monkeypatch.setattr(
        "tessera.services.pipeline.pipeline_lien_refuse.retirer_ces_liens",
        lambda racine, liens: [racine / liens[0]],
    )

    resultat = await finish_lien_refuse(orch, run, LienNonDeclare(["lien"]))  # type: ignore[arg-type]

    assert "non retiré" in (resultat.arret or "")
    assert resultat.commit_sha is None


async def test_the_tester_runs_nothing_when_the_diff_raises_a_link_error() -> None:
    workspace = SimpleNamespace(diff_depuis_base=AsyncMock(side_effect=LienNonDeclare(["lien"])))
    orch = _Orch(Path("."), workspace)
    orch._test_runner = AsyncMock()

    with pytest.raises(LienNonDeclare):
        await pipeline_testeur.run_tests(orch, _run())  # type: ignore[arg-type]

    orch._test_runner.run_tests.assert_not_called()


async def test_other_diff_errors_keep_the_prose_fallback() -> None:
    from tessera.services.git_workspace import GitWorkspaceError

    workspace = SimpleNamespace(diff_depuis_base=AsyncMock(side_effect=GitWorkspaceError("x")))
    orch = _Orch(Path("."), workspace)

    assert await _capture_diff(orch, _run(), "prose") == "prose"  # type: ignore[arg-type]

