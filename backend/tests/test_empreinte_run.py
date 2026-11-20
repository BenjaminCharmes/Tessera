"""Un appel d'agent qui modifie un fichier protégé met le run en blocked — ticket-933."""
from pathlib import Path

import pytest

from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services.noyau.pipeline_events import EventType, OrchestratorEvent, PipelineResult
from tessera.services.pipeline.pipeline_empreinte import gardee
from tessera.services.pipeline.pipeline_run import PipelineRun
from tests.doubles_git import GitWorkspaceDouble


class _Git(GitWorkspaceDouble):
    async def commit_all(self, message: str) -> str:
        return "abc1234"


class _Tickets:
    def __init__(self) -> None:
        self.statut: TicketStatus | None = None

    async def update_status(self, ticket_id: str, status: TicketStatus) -> None:
        self.statut = status


class _Orch:
    def __init__(self, projet: Path) -> None:
        self._git_workspace = _Git()
        self._ticket_svc = _Tickets()
        self._project_path = projet
        self._test_command = None
        self._max_review_rounds = 3
        self.logs: list[str] = []

    def _log(self, message: str) -> None:
        self.logs.append(message)


def _run(events: list[OrchestratorEvent]) -> PipelineRun:
    async def _on_event(event: OrchestratorEvent) -> None:
        events.append(event)

    run = PipelineRun(
        project_id="p",
        ticket=Ticket(
            id="ticket-001", title="T", type=TicketType.feat,
            status=TicketStatus.in_progress, priority=TicketPriority.medium,
            agent="codeur", body="",
        ),
        on_event=_on_event,
    )
    run.branch = "ticket-001-x"
    run.round_num = 1
    return run


async def _appel_qui_reecrit(chemin: Path, contenu: str) -> str:
    chemin.write_text(contenu, encoding="utf-8")
    return "fait"


async def test_call_rewriting_agents_json_blocks_the_run(tmp_path: Path) -> None:
    (tmp_path / "agents.json").write_text('{"autonomy": "pr"}', encoding="utf-8")
    events: list[OrchestratorEvent] = []
    orch = _Orch(tmp_path)
    appel = _appel_qui_reecrit(tmp_path / "agents.json", '{"autonomy": "merge"}')

    arret = await gardee(orch, _run(events), appel)  # type: ignore[arg-type]

    assert isinstance(arret, PipelineResult)
    assert arret.final_status is TicketStatus.blocked
    assert arret.approved is False
    assert "agents.json" in (arret.arret or "")
    assert "merge" not in (arret.arret or "")
    assert orch._ticket_svc.statut is TicketStatus.blocked
    raisons = [e.data.get("reason") for e in events if e.type is EventType.ERROR]
    assert "protected_file_modified" in raisons


async def test_call_changing_nothing_protected_lets_the_run_go_on(tmp_path: Path) -> None:
    (tmp_path / "agents.json").write_text("{}", encoding="utf-8")
    orch = _Orch(tmp_path)

    resultat = await gardee(  # type: ignore[arg-type]
        orch, _run([]), _appel_qui_reecrit(tmp_path / "app.py", "x = 1")
    )

    assert resultat == "fait"
    assert orch.logs == []


async def test_a_failing_call_is_not_compared(tmp_path: Path) -> None:
    (tmp_path / "agents.json").write_text("{}", encoding="utf-8")
    orch = _Orch(tmp_path)

    async def _appel_qui_echoue() -> str:
        (tmp_path / "agents.json").write_text('{"a": 1}', encoding="utf-8")
        raise RuntimeError("provider down")

    with pytest.raises(RuntimeError):
        await gardee(orch, _run([]), _appel_qui_echoue())  # type: ignore[arg-type]

    assert orch._ticket_svc.statut is None
