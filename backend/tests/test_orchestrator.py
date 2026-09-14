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
    _parse_reviewer_verdict,
)


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


def _make_orchestrator(
    tmp_path: Path,
    runner: MagicMock | None = None,
    ticket_service: MagicMock | None = None,
    project_context: str = "ctx",
    agent_configs: list[AgentConfig] | None = None,
    max_review_rounds: int = 3,
) -> Orchestrator:
    return Orchestrator(
        runner=runner or MagicMock(),
        ticket_service=ticket_service or MagicMock(),
        project_context=project_context,
        agent_configs=agent_configs or [],
        pipeline_log_path=tmp_path / "memory" / "pipeline-log.md",
        max_review_rounds=max_review_rounds,
    )


async def _noop(event: OrchestratorEvent) -> None:
    pass


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
