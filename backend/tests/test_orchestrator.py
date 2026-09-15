from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from vibe_ide.models.agent import AgentConfig, AgentResult, AgentRole
from vibe_ide.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from vibe_ide.services.orchestrator import (
    EventType,
    Orchestrator,
    OrchestratorEvent,
    PipelineResult,
)

# Le parsing du verdict vit dans pipeline_text depuis ticket-045, et les étapes
# du pipeline dans pipeline_stages depuis ticket-046.
from vibe_ide.services.pipeline_text import _parse_reviewer_verdict
from vibe_ide.services.git_workspace import GitWorkspaceError
from vibe_ide.services.doc_updater import DocUpdateResult
from vibe_ide.services.security_auditor import SecurityAuditResult, SecurityIssue
from vibe_ide.services.validator import ValidationResult


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _make_ticket(**kwargs: object) -> Ticket:
    defaults: dict[str, object] = {
        "id": "ticket-001",
        "title": "Test feature",
        "type": TicketType.feat,
        "status": TicketStatus.todo,
        "priority": TicketPriority.medium,
        "agent": "codeur",
        "body": "Implement the feature.",
    }
    return Ticket(**(defaults | kwargs))


def _make_agent_result(content: str, role: AgentRole = AgentRole.codeur) -> AgentResult:
    return AgentResult(
        role=role,
        ticket_id="ticket-001",
        content=content,
        suggested_status=TicketStatus.in_review,
        duration_ms=100,
    )


def _make_default_ticket_service() -> AsyncMock:
    """Async ticket service double returning a usable ticket by default."""
    svc = AsyncMock()
    ticket = _make_ticket()
    svc.get_ticket.return_value = ticket
    svc.update_status.return_value = ticket
    return svc


def _make_orchestrator(
    tmp_path: Path,
    runner: MagicMock | None = None,
    ticket_service: MagicMock | None = None,
    project_context: str = "ctx",
    agent_configs: list[AgentConfig] | None = None,
    max_review_rounds: int = 3,
    git_workspace: object | None = None,
    security_auditor: object | None = None,
    validator: object | None = None,
    doc_updater: object | None = None,
    project_path: Path | None = None,
) -> Orchestrator:
    return Orchestrator(
        runner=runner or MagicMock(),
        ticket_service=ticket_service or _make_default_ticket_service(),
        project_context=project_context,
        agent_configs=agent_configs or [],
        pipeline_log_path=tmp_path / "memory" / "pipeline-log.md",
        max_review_rounds=max_review_rounds,
        security_auditor=security_auditor,
        validator=validator,
        doc_updater=doc_updater,
        project_path=project_path,
        git_workspace=git_workspace,
    )


async def _noop(event: OrchestratorEvent) -> None:
    pass


DIFF_REEL = "diff --git a/src/foo.py b/src/foo.py\n+SECRET = 'hunter2'\n"


class _FakeGit:
    """GitWorkspaceService double returning a controlled diff."""

    def __init__(self, diff: str = DIFF_REEL) -> None:
        self._diff = diff
        self.commits: list[str] = []
        self.base_ref_advances = 0

    async def create_branch(self, ticket_id: str, slug: str) -> str:
        return f"{ticket_id}-slug"

    async def current_diff(self) -> str:
        return self._diff

    async def is_clean(self) -> bool:
        return True

    async def commit_all(self, message: str) -> str | None:
        self.commits.append(message)
        return "abc1234"

    async def advance_base_ref(self) -> None:
        self.base_ref_advances += 1


class _RecordingRunner:
    """Minimal runner: returns fixed prose and records every call."""

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def run(self, **kwargs: object) -> AgentResult:
        self.calls.append(kwargs)
        role = kwargs["role"]
        content = (
            "APPROVED" if role == AgentRole.reviewer else "prose du codeur"
        )
        return _make_agent_result(content, role=role)  # type: ignore[arg-type]


# ------------------------------------------------------------------
# EventType
# ------------------------------------------------------------------


def test_agent_tool_use_event_existe() -> None:
    from vibe_ide.services.orchestrator import EventType

    assert EventType.AGENT_TOOL_USE.value == "agent_tool_use"


# ------------------------------------------------------------------
# _parse_reviewer_verdict
# ------------------------------------------------------------------


def test_parse_verdict_approved() -> None:
    approved, reason = _parse_reviewer_verdict("Code is clean. APPROVED.")
    assert approved is True
    assert reason == ""


def test_parse_verdict_approved_case_insensitive() -> None:
    approved, _ = _parse_reviewer_verdict("approved — looks great")
    assert approved is True


def test_parse_verdict_changes_requested_with_reason() -> None:
    approved, reason = _parse_reviewer_verdict("CHANGES_REQUESTED: missing unit tests")
    assert approved is False
    assert "missing unit tests" in reason


def test_parse_verdict_changes_requested_no_reason() -> None:
    approved, reason = _parse_reviewer_verdict("CHANGES_REQUESTED")
    assert approved is False


def test_parse_verdict_changes_requested_takes_priority_over_approved() -> None:
    content = "CHANGES_REQUESTED: fix types\n\nOtherwise APPROVED."
    approved, _ = _parse_reviewer_verdict(content)
    assert approved is False


def test_parse_verdict_unclear_response_is_rejected() -> None:
    approved, _ = _parse_reviewer_verdict("Some vague feedback with no verdict.")
    assert approved is False


# ------------------------------------------------------------------
# pick_next_ticket
# ------------------------------------------------------------------


async def test_pick_next_ticket_returns_highest_priority(tmp_path: Path) -> None:
    svc = AsyncMock()
    low = _make_ticket(id="ticket-001", priority=TicketPriority.low)
    high = _make_ticket(id="ticket-002", priority=TicketPriority.high)

    async def _list(status: TicketStatus | None = None) -> list[Ticket]:
        if status == TicketStatus.todo:
            return [low, high]
        return []

    svc.list_tickets = _list
    orc = _make_orchestrator(tmp_path, ticket_service=svc)
    result = await orc.pick_next_ticket("proj")
    assert result is not None
    assert result.id == "ticket-002"


async def test_pick_next_ticket_critical_before_high(tmp_path: Path) -> None:
    svc = AsyncMock()
    high = _make_ticket(id="ticket-001", priority=TicketPriority.high)
    critical = _make_ticket(id="ticket-002", priority=TicketPriority.critical)

    async def _list(status: TicketStatus | None = None) -> list[Ticket]:
        if status == TicketStatus.todo:
            return [high, critical]
        return []

    svc.list_tickets = _list
    orc = _make_orchestrator(tmp_path, ticket_service=svc)
    result = await orc.pick_next_ticket("proj")
    assert result is not None
    assert result.id == "ticket-002"


async def test_pick_next_ticket_respects_dependencies(tmp_path: Path) -> None:
    svc = AsyncMock()
    blocked = _make_ticket(id="ticket-002", priority=TicketPriority.high, depends_on=["ticket-001"])
    free = _make_ticket(id="ticket-003", priority=TicketPriority.low)

    async def _list(status: TicketStatus | None = None) -> list[Ticket]:
        if status == TicketStatus.todo:
            return [blocked, free]
        return []  # ticket-001 is NOT done

    svc.list_tickets = _list
    orc = _make_orchestrator(tmp_path, ticket_service=svc)
    result = await orc.pick_next_ticket("proj")
    assert result is not None
    assert result.id == "ticket-003"


async def test_pick_next_ticket_done_dep_makes_ticket_eligible(tmp_path: Path) -> None:
    svc = AsyncMock()
    dep_done = _make_ticket(id="ticket-001", status=TicketStatus.done)
    candidate = _make_ticket(id="ticket-002", priority=TicketPriority.high, depends_on=["ticket-001"])

    async def _list(status: TicketStatus | None = None) -> list[Ticket]:
        if status == TicketStatus.todo:
            return [candidate]
        if status == TicketStatus.done:
            return [dep_done]
        return []

    svc.list_tickets = _list
    orc = _make_orchestrator(tmp_path, ticket_service=svc)
    result = await orc.pick_next_ticket("proj")
    assert result is not None
    assert result.id == "ticket-002"


async def test_pick_next_ticket_returns_none_when_all_blocked(tmp_path: Path) -> None:
    svc = AsyncMock()
    blocked = _make_ticket(id="ticket-002", depends_on=["ticket-001"])

    async def _list(status: TicketStatus | None = None) -> list[Ticket]:
        if status == TicketStatus.todo:
            return [blocked]
        return []

    svc.list_tickets = _list
    orc = _make_orchestrator(tmp_path, ticket_service=svc)
    result = await orc.pick_next_ticket("proj")
    assert result is None


async def test_pick_next_ticket_returns_none_when_no_tickets(tmp_path: Path) -> None:
    svc = AsyncMock()
    svc.list_tickets = AsyncMock(return_value=[])
    orc = _make_orchestrator(tmp_path, ticket_service=svc)
    result = await orc.pick_next_ticket("proj")
    assert result is None


# ------------------------------------------------------------------
# run_pipeline — happy path
# ------------------------------------------------------------------


async def test_run_pipeline_approved_first_round(tmp_path: Path) -> None:
    ticket = _make_ticket()
    svc = AsyncMock()
    svc.get_ticket.return_value = ticket
    svc.update_status.return_value = ticket

    runner = MagicMock()
    runner.run = AsyncMock(
        side_effect=[
            _make_agent_result("def foo(): pass", AgentRole.codeur),
            _make_agent_result("APPROVED — clean implementation", AgentRole.reviewer),
        ]
    )

    orc = _make_orchestrator(tmp_path, runner=runner, ticket_service=svc)
    result = await orc.run_pipeline("proj", "ticket-001", _noop)

    assert result.approved is True
    assert result.rounds == 1
    assert result.final_status == TicketStatus.done


async def test_run_pipeline_cree_une_branche_et_emet_l_event(tmp_path: Path) -> None:
    """The branch is created before the first round, and announced."""
    events: list[OrchestratorEvent] = []

    class FakeGit:
        def __init__(self) -> None:
            self.created: list[tuple[str, str]] = []

        async def create_branch(self, ticket_id: str, slug: str) -> str:
            self.created.append((ticket_id, slug))
            return f"{ticket_id}-{slug}"

        async def current_diff(self) -> str:
            return ""

        async def is_clean(self) -> bool:
            return True

        async def commit_all(self, message: str) -> str | None:
            return None

    git = FakeGit()
    ticket = _make_ticket()
    svc = AsyncMock()
    svc.get_ticket.return_value = ticket
    svc.update_status.return_value = ticket

    runner = MagicMock()
    runner.run = AsyncMock(
        side_effect=[
            _make_agent_result("def foo(): pass", AgentRole.codeur),
            _make_agent_result("APPROVED — clean implementation", AgentRole.reviewer),
        ]
    )

    orchestrator = _make_orchestrator(
        tmp_path, runner=runner, ticket_service=svc, git_workspace=git
    )

    async def on_event(event: OrchestratorEvent) -> None:
        events.append(event)

    result = await orchestrator.run_pipeline("projet", "ticket-001", on_event)

    assert len(git.created) == 1
    branch_events = [e for e in events if e.type == EventType.BRANCH_CREATED]
    assert len(branch_events) == 1
    assert branch_events[0].data["branch"] == git.created[0][0] + "-" + git.created[0][1]
    assert result.branch == branch_events[0].data["branch"]


async def test_run_pipeline_sans_git_workspace_reste_fonctionnel(tmp_path: Path) -> None:
    """git_workspace is optional: without it the pipeline runs as before."""
    events: list[OrchestratorEvent] = []
    ticket = _make_ticket()
    svc = AsyncMock()
    svc.get_ticket.return_value = ticket
    svc.update_status.return_value = ticket

    runner = MagicMock()
    runner.run = AsyncMock(
        side_effect=[
            _make_agent_result("def foo(): pass", AgentRole.codeur),
            _make_agent_result("APPROVED — clean implementation", AgentRole.reviewer),
        ]
    )

    orchestrator = _make_orchestrator(
        tmp_path, runner=runner, ticket_service=svc, git_workspace=None
    )

    async def on_event(event: OrchestratorEvent) -> None:
        events.append(event)

    result = await orchestrator.run_pipeline("projet", "ticket-001", on_event)

    assert not [e for e in events if e.type == EventType.BRANCH_CREATED]
    assert result.branch is None


async def test_run_pipeline_approved_second_round(tmp_path: Path) -> None:
    ticket = _make_ticket()
    svc = AsyncMock()
    svc.get_ticket.return_value = ticket
    svc.update_status.return_value = ticket

    runner = MagicMock()
    runner.run = AsyncMock(
        side_effect=[
            _make_agent_result("draft code", AgentRole.codeur),
            _make_agent_result("CHANGES_REQUESTED: add docstrings", AgentRole.reviewer),
            _make_agent_result("fixed code with docstrings", AgentRole.codeur),
            _make_agent_result("APPROVED", AgentRole.reviewer),
        ]
    )

    orc = _make_orchestrator(tmp_path, runner=runner, ticket_service=svc)
    result = await orc.run_pipeline("proj", "ticket-001", _noop)

    assert result.approved is True
    assert result.rounds == 2


async def test_run_pipeline_blocked_after_max_rounds(tmp_path: Path) -> None:
    ticket = _make_ticket()
    svc = AsyncMock()
    svc.get_ticket.return_value = ticket
    svc.update_status.return_value = ticket

    runner = MagicMock()
    runner.run = AsyncMock(
        side_effect=[
            _make_agent_result("code v1", AgentRole.codeur),
            _make_agent_result("CHANGES_REQUESTED: no tests", AgentRole.reviewer),
            _make_agent_result("code v2", AgentRole.codeur),
            _make_agent_result("CHANGES_REQUESTED: still no tests", AgentRole.reviewer),
            _make_agent_result("code v3", AgentRole.codeur),
            _make_agent_result("CHANGES_REQUESTED: really needs tests", AgentRole.reviewer),
        ]
    )

    orc = _make_orchestrator(tmp_path, runner=runner, ticket_service=svc, max_review_rounds=3)
    result = await orc.run_pipeline("proj", "ticket-001", _noop)

    assert result.approved is False
    assert result.rounds == 3
    assert result.final_status == TicketStatus.blocked


async def test_run_pipeline_raises_when_ticket_not_found(tmp_path: Path) -> None:
    svc = AsyncMock()
    svc.get_ticket.return_value = None

    orc = _make_orchestrator(tmp_path, ticket_service=svc)
    with pytest.raises(ValueError, match="introuvable"):
        await orc.run_pipeline("proj", "ticket-999", _noop)


# ------------------------------------------------------------------
# run_pipeline — events
# ------------------------------------------------------------------


async def test_run_pipeline_emits_required_event_types(tmp_path: Path) -> None:
    ticket = _make_ticket()
    svc = AsyncMock()
    svc.get_ticket.return_value = ticket
    svc.update_status.return_value = ticket

    runner = MagicMock()
    runner.run = AsyncMock(
        side_effect=[
            _make_agent_result("code", AgentRole.codeur),
            _make_agent_result("APPROVED", AgentRole.reviewer),
        ]
    )

    events: list[OrchestratorEvent] = []

    async def capture(e: OrchestratorEvent) -> None:
        events.append(e)

    orc = _make_orchestrator(tmp_path, runner=runner, ticket_service=svc)
    await orc.run_pipeline("proj", "ticket-001", capture)

    emitted = {e.type for e in events}
    assert EventType.TICKET_STATUS_CHANGED in emitted
    assert EventType.AGENT_STARTED in emitted
    assert EventType.AGENT_DONE in emitted
    assert EventType.PIPELINE_DONE in emitted


async def test_run_pipeline_emits_pipeline_done_with_approved_flag(tmp_path: Path) -> None:
    ticket = _make_ticket()
    svc = AsyncMock()
    svc.get_ticket.return_value = ticket
    svc.update_status.return_value = ticket

    runner = MagicMock()
    runner.run = AsyncMock(
        side_effect=[
            _make_agent_result("code", AgentRole.codeur),
            _make_agent_result("APPROVED", AgentRole.reviewer),
        ]
    )

    events: list[OrchestratorEvent] = []

    async def capture(e: OrchestratorEvent) -> None:
        events.append(e)

    orc = _make_orchestrator(tmp_path, runner=runner, ticket_service=svc)
    await orc.run_pipeline("proj", "ticket-001", capture)

    done_events = [e for e in events if e.type == EventType.PIPELINE_DONE]
    assert len(done_events) == 1
    assert done_events[0].data["approved"] is True


async def test_run_pipeline_emits_agent_started_for_both_roles(tmp_path: Path) -> None:
    ticket = _make_ticket()
    svc = AsyncMock()
    svc.get_ticket.return_value = ticket
    svc.update_status.return_value = ticket

    runner = MagicMock()
    runner.run = AsyncMock(
        side_effect=[
            _make_agent_result("code", AgentRole.codeur),
            _make_agent_result("APPROVED", AgentRole.reviewer),
        ]
    )

    events: list[OrchestratorEvent] = []

    async def capture(e: OrchestratorEvent) -> None:
        events.append(e)

    orc = _make_orchestrator(tmp_path, runner=runner, ticket_service=svc)
    await orc.run_pipeline("proj", "ticket-001", capture)

    started_agents = {e.agent for e in events if e.type == EventType.AGENT_STARTED}
    assert AgentRole.codeur in started_agents
    assert AgentRole.reviewer in started_agents


async def test_run_pipeline_emits_agent_tool_use_event(tmp_path: Path) -> None:
    ticket = _make_ticket()
    svc = AsyncMock()
    svc.get_ticket.return_value = ticket
    svc.update_status.return_value = ticket

    async def fake_run(
        role: AgentRole,
        ticket: Ticket,
        project_context: str,
        agent_config: AgentConfig | None = None,
        stream_callback: object = None,
        tool_callback: object = None,
        run_id: str | None = None,
    ) -> AgentResult:
        # Mime le comportement de ClaudeAgentSDKProvider : le tool_callback
        # est réellement awaité pendant l'exécution du codeur.
        if role == AgentRole.codeur and tool_callback is not None:
            await tool_callback("Write", {"file_path": "src/foo.py"})  # type: ignore[operator]
        if role == AgentRole.reviewer:
            return _make_agent_result("APPROVED", AgentRole.reviewer)
        return _make_agent_result("code", AgentRole.codeur)

    runner = MagicMock()
    runner.run = fake_run

    events: list[OrchestratorEvent] = []

    async def capture(e: OrchestratorEvent) -> None:
        events.append(e)

    orc = _make_orchestrator(tmp_path, runner=runner, ticket_service=svc)
    await orc.run_pipeline("proj", "ticket-001", capture)

    tool_events = [e for e in events if e.type == EventType.AGENT_TOOL_USE]
    assert len(tool_events) == 1
    tool_event = tool_events[0]
    assert tool_event.agent == AgentRole.codeur
    assert tool_event.ticket_id == "ticket-001"
    assert tool_event.data == {"tool": "Write", "input": {"file_path": "src/foo.py"}}


async def test_run_pipeline_ticket_status_progression(tmp_path: Path) -> None:
    ticket = _make_ticket()
    svc = AsyncMock()
    svc.get_ticket.return_value = ticket
    svc.update_status.return_value = ticket

    runner = MagicMock()
    runner.run = AsyncMock(
        side_effect=[
            _make_agent_result("code", AgentRole.codeur),
            _make_agent_result("APPROVED", AgentRole.reviewer),
        ]
    )

    statuses: list[str] = []

    async def capture(e: OrchestratorEvent) -> None:
        if e.type == EventType.TICKET_STATUS_CHANGED:
            statuses.append(e.data["status"])

    orc = _make_orchestrator(tmp_path, runner=runner, ticket_service=svc)
    await orc.run_pipeline("proj", "ticket-001", capture)

    assert TicketStatus.in_progress.value in statuses
    assert TicketStatus.in_review.value in statuses
    assert TicketStatus.done.value in statuses


# ------------------------------------------------------------------
# run_pipeline — reviewer feedback passed to codeur
# ------------------------------------------------------------------


async def test_run_pipeline_feedback_included_in_second_round_context(tmp_path: Path) -> None:
    ticket = _make_ticket()
    svc = AsyncMock()
    svc.get_ticket.return_value = ticket
    svc.update_status.return_value = ticket

    captured_contexts: list[str] = []

    async def fake_run(
        role: AgentRole,
        ticket: Ticket,
        project_context: str,
        agent_config: AgentConfig | None = None,
        stream_callback: object = None,
        tool_callback: object = None,
        run_id: str | None = None,
    ) -> AgentResult:
        if role == AgentRole.codeur:
            captured_contexts.append(project_context)
        if role == AgentRole.reviewer and len(captured_contexts) == 1:
            return _make_agent_result("CHANGES_REQUESTED: add error handling", AgentRole.reviewer)
        if role == AgentRole.reviewer:
            return _make_agent_result("APPROVED", AgentRole.reviewer)
        return _make_agent_result("code", AgentRole.codeur)

    runner = MagicMock()
    runner.run = fake_run

    orc = _make_orchestrator(tmp_path, runner=runner, ticket_service=svc)
    await orc.run_pipeline("proj", "ticket-001", _noop)

    assert len(captured_contexts) == 2
    assert "add error handling" in captured_contexts[1]


# ------------------------------------------------------------------
# run_pipeline — pipeline log
# ------------------------------------------------------------------


async def test_run_pipeline_writes_to_pipeline_log(tmp_path: Path) -> None:
    ticket = _make_ticket()
    svc = AsyncMock()
    svc.get_ticket.return_value = ticket
    svc.update_status.return_value = ticket

    runner = MagicMock()
    runner.run = AsyncMock(
        side_effect=[
            _make_agent_result("code", AgentRole.codeur),
            _make_agent_result("APPROVED", AgentRole.reviewer),
        ]
    )

    orc = _make_orchestrator(tmp_path, runner=runner, ticket_service=svc)
    await orc.run_pipeline("proj", "ticket-001", _noop)

    log_path = tmp_path / "memory" / "pipeline-log.md"
    assert log_path.exists()
    content = log_path.read_text(encoding="utf-8")
    assert "ticket-001" in content
    assert "APPROVED" in content


# ------------------------------------------------------------------
# run_autonomous
# ------------------------------------------------------------------


async def test_run_autonomous_processes_multiple_tickets(tmp_path: Path) -> None:
    ticket_a = _make_ticket(id="ticket-001")
    ticket_b = _make_ticket(id="ticket-002")

    pick_calls = 0

    async def mock_pick(project_id: str) -> Ticket | None:
        nonlocal pick_calls
        pick_calls += 1
        if pick_calls == 1:
            return ticket_a
        if pick_calls == 2:
            return ticket_b
        return None

    async def mock_pipeline(project_id: str, ticket_id: str, on_event: object) -> PipelineResult:
        return PipelineResult(
            ticket_id=ticket_id,
            final_status=TicketStatus.done,
            rounds=1,
            approved=True,
        )

    orc = _make_orchestrator(tmp_path)
    orc.pick_next_ticket = mock_pick  # type: ignore[method-assign]
    orc.run_pipeline = mock_pipeline  # type: ignore[method-assign]

    results = await orc.run_autonomous("proj", max_tickets=5)
    assert len(results) == 2
    assert results[0].ticket_id == "ticket-001"
    assert results[1].ticket_id == "ticket-002"


async def test_run_autonomous_stops_at_max_tickets(tmp_path: Path) -> None:
    ticket = _make_ticket()

    async def mock_pick(project_id: str) -> Ticket | None:
        return ticket  # always returns a ticket

    async def mock_pipeline(project_id: str, ticket_id: str, on_event: object) -> PipelineResult:
        return PipelineResult(
            ticket_id=ticket_id,
            final_status=TicketStatus.done,
            rounds=1,
            approved=True,
        )

    orc = _make_orchestrator(tmp_path)
    orc.pick_next_ticket = mock_pick  # type: ignore[method-assign]
    orc.run_pipeline = mock_pipeline  # type: ignore[method-assign]

    results = await orc.run_autonomous("proj", max_tickets=2)
    assert len(results) == 2


async def test_run_autonomous_stops_when_no_tickets(tmp_path: Path) -> None:
    async def mock_pick(project_id: str) -> Ticket | None:
        return None

    orc = _make_orchestrator(tmp_path)
    orc.pick_next_ticket = mock_pick  # type: ignore[method-assign]

    results = await orc.run_autonomous("proj", max_tickets=5)
    assert results == []


async def test_run_autonomous_emits_events_via_callback(tmp_path: Path) -> None:
    ticket = _make_ticket()
    pick_calls = 0

    async def mock_pick(project_id: str) -> Ticket | None:
        nonlocal pick_calls
        pick_calls += 1
        return ticket if pick_calls == 1 else None

    events: list[OrchestratorEvent] = []

    async def mock_pipeline(
        project_id: str, ticket_id: str, on_event: object
    ) -> PipelineResult:
        import inspect
        if callable(on_event) and inspect.iscoroutinefunction(on_event):
            await on_event(  # type: ignore[operator]
                OrchestratorEvent(
                    type=EventType.PIPELINE_DONE,
                    ticket_id=ticket_id,
                    data={"approved": True, "rounds": 1},
                )
            )
        return PipelineResult(
            ticket_id=ticket_id,
            final_status=TicketStatus.done,
            rounds=1,
            approved=True,
        )

    async def capture(e: OrchestratorEvent) -> None:
        events.append(e)

    orc = _make_orchestrator(tmp_path)
    orc.pick_next_ticket = mock_pick  # type: ignore[method-assign]
    orc.run_pipeline = mock_pipeline  # type: ignore[method-assign]

    await orc.run_autonomous("proj", max_tickets=5, on_event=capture)
    assert len(events) == 1
    assert events[0].type == EventType.PIPELINE_DONE


# ------------------------------------------------------------------
# run_pipeline — real git diff feeds reviewer, auditor and validator
# ------------------------------------------------------------------


async def test_l_auditeur_securite_recoit_le_diff_reel(tmp_path: Path) -> None:
    audits: list[str] = []

    class _FakeAuditor:
        async def audit(self, code_diff: str, project_path: Path) -> object:
            audits.append(code_diff)
            return SecurityAuditResult(verdict="PASS", issues=[], summary="rien")

    orchestrator = _make_orchestrator(
        tmp_path,
        runner=_RecordingRunner(),
        git_workspace=_FakeGit(),
        security_auditor=_FakeAuditor(),
        project_path=tmp_path,
    )
    await orchestrator.run_pipeline("projet", "ticket-001", _noop)

    assert audits, "l'auditeur n'a pas été appelé"
    assert "SECRET = 'hunter2'" in audits[0]
    assert "prose du codeur" not in audits[0]


async def test_le_validateur_recoit_le_diff_reel(tmp_path: Path) -> None:
    validated: list[str] = []

    class _FakeValidator:
        async def validate(
            self, criteria: list[str], code_produced: str, test_result: object
        ) -> object:
            validated.append(code_produced)
            return ValidationResult(
                all_passed=True, criteria=[], verdict="APPROVED", feedback=""
            )

    orchestrator = _make_orchestrator(
        tmp_path,
        runner=_RecordingRunner(),
        git_workspace=_FakeGit(),
        validator=_FakeValidator(),
        project_path=tmp_path,
    )
    await orchestrator.run_pipeline("projet", "ticket-001", _noop)

    assert validated, "le validateur n'a pas été appelé"
    assert "SECRET = 'hunter2'" in validated[0]


async def test_le_reviewer_recoit_le_diff_reel(tmp_path: Path) -> None:
    runner = _RecordingRunner()
    orchestrator = _make_orchestrator(
        tmp_path, runner=runner, git_workspace=_FakeGit(), project_path=tmp_path
    )
    await orchestrator.run_pipeline("projet", "ticket-001", _noop)

    reviewer_calls = [c for c in runner.calls if c["role"] == AgentRole.reviewer]
    assert reviewer_calls, "le reviewer n'a pas été appelé"
    assert "SECRET = 'hunter2'" in str(reviewer_calls[0]["project_context"])


async def test_sans_git_workspace_on_retombe_sur_la_prose_du_codeur(
    tmp_path: Path,
) -> None:
    """Historical behaviour preserved when no git repository is available."""
    runner = _RecordingRunner()
    orchestrator = _make_orchestrator(
        tmp_path, runner=runner, git_workspace=None, project_path=tmp_path
    )
    await orchestrator.run_pipeline("projet", "ticket-001", _noop)

    reviewer_calls = [c for c in runner.calls if c["role"] == AgentRole.reviewer]
    assert "prose du codeur" in str(reviewer_calls[0]["project_context"])


async def test_diff_vide_retombe_sur_la_prose_du_codeur(tmp_path: Path) -> None:
    """An empty diff means the coder wrote nothing: its prose is the only
    material left."""
    runner = _RecordingRunner()
    orchestrator = _make_orchestrator(
        tmp_path,
        runner=runner,
        git_workspace=_FakeGit(diff="   \n"),
        project_path=tmp_path,
    )
    await orchestrator.run_pipeline("projet", "ticket-001", _noop)

    reviewer_calls = [c for c in runner.calls if c["role"] == AgentRole.reviewer]
    assert "prose du codeur" in str(reviewer_calls[0]["project_context"])


async def test_le_doc_updater_recoit_le_diff_reel(tmp_path: Path) -> None:
    """The doc-updater must document what actually changed on disk, not the
    coder's prose summary of it."""
    updated: list[str] = []

    class _FakeDocUpdater:
        async def update_docs(
            self, project_path: Path, diff: str, ticket_title: str
        ) -> DocUpdateResult:
            updated.append(diff)
            return DocUpdateResult(no_changes=False, files_updated=["README.md"])

    orchestrator = _make_orchestrator(
        tmp_path,
        runner=_RecordingRunner(),
        git_workspace=_FakeGit(),
        doc_updater=_FakeDocUpdater(),
        project_path=tmp_path,
    )
    await orchestrator.run_pipeline("projet", "ticket-001", _noop)

    assert updated, "le doc-updater n'a pas été appelé"
    assert "SECRET = 'hunter2'" in updated[0]
    assert "prose du codeur" not in updated[0]


async def test_doc_updater_sans_git_workspace_retombe_sur_la_prose_du_codeur(
    tmp_path: Path,
) -> None:
    """Historical behaviour preserved when no git repository is available."""
    updated: list[str] = []

    class _FakeDocUpdater:
        async def update_docs(
            self, project_path: Path, diff: str, ticket_title: str
        ) -> DocUpdateResult:
            updated.append(diff)
            return DocUpdateResult(no_changes=False, files_updated=["README.md"])

    orchestrator = _make_orchestrator(
        tmp_path,
        runner=_RecordingRunner(),
        git_workspace=None,
        doc_updater=_FakeDocUpdater(),
        project_path=tmp_path,
    )
    await orchestrator.run_pipeline("projet", "ticket-001", _noop)

    assert updated, "le doc-updater n'a pas été appelé"


# ------------------------------------------------------------------
# Commit sur verdict APPROVED
# ------------------------------------------------------------------


async def test_commit_sur_verdict_approuve(tmp_path: Path) -> None:
    """An approved pipeline commits on its branch."""
    events: list[OrchestratorEvent] = []
    git = _FakeGit()

    async def on_event(event: OrchestratorEvent) -> None:
        events.append(event)

    orchestrator = _make_orchestrator(
        tmp_path, runner=_RecordingRunner(), git_workspace=git, project_path=tmp_path
    )
    result = await orchestrator.run_pipeline("projet", "ticket-001", on_event)

    assert len(git.commits) == 1
    assert "ticket-001" in git.commits[0]
    assert result.commit_sha == "abc1234"

    commit_events = [e for e in events if e.type == EventType.COMMIT_CREATED]
    assert len(commit_events) == 1
    assert commit_events[0].data["sha"] == "abc1234"


async def test_commit_utilise_le_type_du_ticket(tmp_path: Path) -> None:
    """The commit message prefix must reflect ticket.type, not a hardcoded "feat:"."""
    events: list[OrchestratorEvent] = []
    git = _FakeGit()

    async def on_event(event: OrchestratorEvent) -> None:
        events.append(event)

    svc = AsyncMock()
    fix_ticket = _make_ticket(type=TicketType.fix)
    svc.get_ticket.return_value = fix_ticket
    svc.update_status.return_value = fix_ticket

    orchestrator = _make_orchestrator(
        tmp_path,
        runner=_RecordingRunner(),
        ticket_service=svc,
        git_workspace=git,
        project_path=tmp_path,
    )
    await orchestrator.run_pipeline("projet", "ticket-001", on_event)

    assert len(git.commits) == 1
    assert git.commits[0].startswith("fix:")
    assert not git.commits[0].startswith("feat:")


async def test_commit_chore_sur_changes_requested(tmp_path: Path) -> None:
    """A non-approved pipeline still commits its work, under a Conventional
    Commits `chore:` message (never `wip:`, which is not a valid type), on
    its own ticket branch — inspection happens via `git show`/`git diff` on
    that branch rather than through a dirty tree."""
    git = _FakeGit()

    class _RefusingRunner(_RecordingRunner):
        async def run(self, **kwargs: object) -> AgentResult:
            self.calls.append(kwargs)
            role = kwargs["role"]
            content = (
                "CHANGES_REQUESTED: revoir la gestion d'erreur"
                if role == AgentRole.reviewer
                else "prose du codeur"
            )
            return _make_agent_result(content, role=role)  # type: ignore[arg-type]

    orchestrator = _make_orchestrator(
        tmp_path, runner=_RefusingRunner(), git_workspace=git, project_path=tmp_path
    )
    result = await orchestrator.run_pipeline("projet", "ticket-001", _noop)

    assert len(git.commits) == 1
    assert git.commits[0].startswith("chore: ticket-001")
    assert "unapproved work" in git.commits[0]
    assert result.commit_sha == "abc1234"


async def test_commit_chore_quand_la_securite_bloque(tmp_path: Path) -> None:
    """The early exit on BLOCK still commits the coder's work under a
    Conventional Commits `chore:` message, so it survives on the ticket's
    branch for inspection."""
    git = _FakeGit()

    class _BlockingAuditor:
        async def audit(self, code_diff: str, project_path: Path) -> object:
            # has_critical/has_high sont des propriétés dérivées de `issues`
            # sur le vrai SecurityAuditResult (pas des champs d'init) : on
            # passe une CRITICAL réelle plutôt que les kwargs du brief.
            return SecurityAuditResult(
                verdict="BLOCK",
                issues=[
                    SecurityIssue(
                        severity="CRITICAL",
                        type="hardcoded_secret",
                        location="src/foo.py",
                        description="secret en dur",
                        fix="utiliser une variable d'environnement",
                    )
                ],
                summary="secret detecte",
            )

    orchestrator = _make_orchestrator(
        tmp_path,
        runner=_RecordingRunner(),
        git_workspace=git,
        security_auditor=_BlockingAuditor(),
        project_path=tmp_path,
    )
    result = await orchestrator.run_pipeline("projet", "ticket-001", _noop)

    assert len(git.commits) == 1
    assert git.commits[0].startswith("chore: ticket-001")
    assert "security block" in git.commits[0]
    assert result.commit_sha == "abc1234"


# ------------------------------------------------------------------
# Finding 1 — a failed branch creation must never lead to a commit
# ------------------------------------------------------------------


class _FailingBranchGit(_FakeGit):
    """create_branch always fails; the rest of the pipeline still works."""

    async def create_branch(self, ticket_id: str, slug: str) -> str:
        raise GitWorkspaceError("checkout -b failed: local modifications")


async def test_branche_en_echec_le_pipeline_termine_sans_commettre(tmp_path: Path) -> None:
    """Regression test for Finding 1: gate commit on `branch`, not just on
    git_workspace being configured — a failed branch creation must not
    result in a commit onto whatever ref happens to be checked out."""
    git = _FailingBranchGit()

    orchestrator = _make_orchestrator(
        tmp_path, runner=_RecordingRunner(), git_workspace=git, project_path=tmp_path
    )
    result = await orchestrator.run_pipeline("projet", "ticket-001", _noop)

    assert result.approved is True
    assert result.branch is None
    assert git.commits == []
    assert result.commit_sha is None


# ------------------------------------------------------------------
# Finding 3 — current_diff failure still falls back to the coder's prose
# ------------------------------------------------------------------


class _FailingDiffGit(_FakeGit):
    """current_diff always fails; the pipeline must still complete."""

    async def current_diff(self) -> str:
        raise GitWorkspaceError("git diff failed")


async def test_diff_en_echec_retombe_sur_la_prose_et_termine(tmp_path: Path) -> None:
    runner = _RecordingRunner()
    git = _FailingDiffGit()

    orchestrator = _make_orchestrator(
        tmp_path, runner=runner, git_workspace=git, project_path=tmp_path
    )
    result = await orchestrator.run_pipeline("projet", "ticket-001", _noop)

    assert result.approved is True
    reviewer_calls = [c for c in runner.calls if c["role"] == AgentRole.reviewer]
    assert "prose du codeur" in str(reviewer_calls[0]["project_context"])


# ------------------------------------------------------------------
# Finding 2 — autonomous mode must not chain a dirty tree across tickets
# ------------------------------------------------------------------


class _DirtyingGit:
    """Simulates a real repo: refuses (unapproved) work leaves the tree
    dirty; commits reset it clean. is_clean() reports the real state so
    the orchestrator's dirty-tree guard can be exercised end-to-end."""

    def __init__(self) -> None:
        self._dirty = False
        self.commits: list[str] = []
        self.branches_created: list[str] = []
        self.base_ref_advances = 0

    async def create_branch(self, ticket_id: str, slug: str) -> str:
        self.branches_created.append(ticket_id)
        return f"{ticket_id}-slug"

    async def current_diff(self) -> str:
        return DIFF_REEL

    async def is_clean(self) -> bool:
        return not self._dirty

    async def commit_all(self, message: str) -> str | None:
        self.commits.append(message)
        self._dirty = False
        return "abc1234"

    async def advance_base_ref(self) -> None:
        self.base_ref_advances += 1

    def mark_dirty(self) -> None:
        self._dirty = True


async def test_autonomous_ne_commet_pas_le_travail_non_approuve_du_ticket_precedent(
    tmp_path: Path,
) -> None:
    """Ticket 1 is refused; its work is committed under its own `wip:` message
    on its own branch, so ticket 2 starts from a clean tree and can never
    commit ticket 1's rejected work under its own name."""
    git = _DirtyingGit()
    ticket_a = _make_ticket(id="ticket-001")
    ticket_b = _make_ticket(id="ticket-002")

    svc = AsyncMock()
    svc.get_ticket.side_effect = lambda tid: ticket_a if tid == "ticket-001" else ticket_b
    svc.update_status.return_value = ticket_a

    class _RefusingThenDirtyingRunner(_RecordingRunner):
        async def run(self, **kwargs: object) -> AgentResult:
            self.calls.append(kwargs)
            role = kwargs["role"]
            ticket = kwargs["ticket"]
            if role == AgentRole.codeur:
                return _make_agent_result("prose du codeur", role=role)
            # ticket-001 is refused and leaves the tree dirty; ticket-002 is
            # approved.
            if ticket.id == "ticket-001":
                git.mark_dirty()
                return _make_agent_result(
                    "CHANGES_REQUESTED: pas assez de tests", role=role
                )
            return _make_agent_result("APPROVED", role=role)

    orchestrator = _make_orchestrator(
        tmp_path,
        runner=_RefusingThenDirtyingRunner(),
        ticket_service=svc,
        git_workspace=git,
        project_path=tmp_path,
        max_review_rounds=1,
    )

    pick_calls = 0

    async def mock_pick(project_id: str) -> Ticket | None:
        nonlocal pick_calls
        pick_calls += 1
        if pick_calls == 1:
            return ticket_a
        if pick_calls == 2:
            return ticket_b
        return None

    orchestrator.pick_next_ticket = mock_pick  # type: ignore[method-assign]

    results = await orchestrator.run_autonomous("proj", max_tickets=5)

    assert len(results) == 2
    # ticket-001 was blocked (max rounds reached) but its work is still
    # committed — under a `chore:` message naming ticket-001, never under
    # the ticket's own type.
    assert results[0].ticket_id == "ticket-001"
    assert results[0].approved is False
    assert git.commits[0].startswith("chore: ticket-001")

    # Because ticket-001 committed, ticket-002 starts from a clean tree and
    # runs normally; its own commit carries only its own name.
    assert results[1].ticket_id == "ticket-002"
    assert results[1].approved is True
    assert git.commits[1] == "feat: ticket-002 — Test feature"
    assert len(git.commits) == 2


async def test_message_de_commit_non_approuve_tient_sur_une_seule_ligne(
    tmp_path: Path,
) -> None:
    """The security summary is interpolated into a commit *subject*: any
    newline in it would split the message into subject + body and leave a
    truncated, misleading one-liner in `git log --oneline`."""
    git = _FakeGit()

    class _MultilineBlockingAuditor:
        async def audit(self, code_diff: str, project_path: Path) -> object:
            return SecurityAuditResult(
                verdict="BLOCK",
                issues=[
                    SecurityIssue(
                        severity="CRITICAL",
                        type="hardcoded_secret",
                        location="src/foo.py",
                        description="secret en dur",
                        fix="utiliser une variable d'environnement",
                    )
                ],
                summary="secret detecte\n\nplusieurs lignes\ndans le resume",
            )

    orchestrator = _make_orchestrator(
        tmp_path,
        runner=_RecordingRunner(),
        git_workspace=git,
        security_auditor=_MultilineBlockingAuditor(),
        project_path=tmp_path,
    )
    await orchestrator.run_pipeline("projet", "ticket-001", _noop)

    assert len(git.commits) == 1
    assert "\n" not in git.commits[0]


async def test_base_ref_avance_apres_une_approbation(tmp_path: Path) -> None:
    """An approved ticket's work becomes the base the next ticket forks from,
    so a plan of sequential tickets is not run against a stale base."""
    git = _FakeGit()
    orchestrator = _make_orchestrator(
        tmp_path, runner=_RecordingRunner(), git_workspace=git, project_path=tmp_path
    )
    result = await orchestrator.run_pipeline("projet", "ticket-001", _noop)

    assert result.approved is True
    assert git.base_ref_advances == 1


async def test_base_ref_n_avance_pas_sur_un_travail_non_approuve(
    tmp_path: Path,
) -> None:
    """Rejected work must stay off the base ref: the next ticket has to fork
    from the last *approved* state, never from a `chore:` commit."""
    git = _FakeGit()

    class _RefusingRunner(_RecordingRunner):
        async def run(self, **kwargs: object) -> AgentResult:
            self.calls.append(kwargs)
            role = kwargs["role"]
            content = (
                "CHANGES_REQUESTED: manque des tests"
                if role == AgentRole.reviewer
                else "prose du codeur"
            )
            return _make_agent_result(content, role=role)  # type: ignore[arg-type]

    orchestrator = _make_orchestrator(
        tmp_path, runner=_RefusingRunner(), git_workspace=git, project_path=tmp_path
    )
    result = await orchestrator.run_pipeline("projet", "ticket-001", _noop)

    assert result.approved is False
    assert git.base_ref_advances == 0
