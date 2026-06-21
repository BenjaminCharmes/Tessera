from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from vibe_ide.agents.github_sync import GithubSyncAgent, SyncResult, _extract_type
from vibe_ide.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from vibe_ide.services.github_service import GitHubIssue
from vibe_ide.services.sync_map import SyncEntry, SyncMapService


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _make_issue(
    number: int = 42,
    title: str = "Fix login bug",
    body: str = "Users can't log in.",
    html_url: str = "https://github.com/owner/repo/issues/42",
    labels: list[str] | None = None,
) -> GitHubIssue:
    return GitHubIssue(
        number=number,
        title=title,
        body=body,
        html_url=html_url,
        labels=labels or ["agent-ready"],
    )


def _make_ticket(
    ticket_id: str = "ticket-001",
    github_issue_url: str | None = None,
    status: TicketStatus = TicketStatus.todo,
    ticket_type: TicketType = TicketType.feat,
    title: str = "Some ticket",
    body: str = "",
) -> Ticket:
    return Ticket(
        id=ticket_id,
        title=title,
        type=ticket_type,
        status=status,
        priority=TicketPriority.medium,
        agent="codeur",
        github_issue_url=github_issue_url,
        body=body,
    )


def _make_agent(
    github_svc: MagicMock | None = None,
    ticket_svc: MagicMock | None = None,
    sync_map_svc: SyncMapService | None = None,
    project_path: Path | None = None,
    label_map: dict[str, str] | None = None,
) -> GithubSyncAgent:
    return GithubSyncAgent(
        github_svc=github_svc or AsyncMock(),
        ticket_svc=ticket_svc or AsyncMock(),
        sync_map_svc=sync_map_svc or _mock_sync_map(),
        project_path=project_path or Path("/tmp/test-project"),
        label_map=label_map,
    )


def _mock_sync_map(mapping: dict[str, SyncEntry] | None = None) -> SyncMapService:
    svc = MagicMock(spec=SyncMapService)
    svc.load.return_value = mapping or {}
    svc.save.return_value = None
    svc.issue_for_ticket.side_effect = lambda m, tid: m[tid].issue if tid in m else None
    svc.ticket_for_issue.side_effect = lambda m, num: next(
        (k for k, v in m.items() if v.issue == num), None
    )
    return svc


# ------------------------------------------------------------------
# _extract_type
# ------------------------------------------------------------------


def test_extract_type_feat_label() -> None:
    assert _extract_type(["agent-ready", "feat"]) == TicketType.feat


def test_extract_type_feature_label() -> None:
    assert _extract_type(["feature"]) == TicketType.feat


def test_extract_type_fix_label() -> None:
    assert _extract_type(["fix"]) == TicketType.fix


def test_extract_type_bug_label() -> None:
    assert _extract_type(["bug"]) == TicketType.fix


def test_extract_type_chore_label() -> None:
    assert _extract_type(["chore"]) == TicketType.chore


def test_extract_type_docs_label() -> None:
    assert _extract_type(["docs"]) == TicketType.docs


def test_extract_type_documentation_label() -> None:
    assert _extract_type(["documentation"]) == TicketType.docs


def test_extract_type_design_label() -> None:
    assert _extract_type(["design"]) == TicketType.design


def test_extract_type_case_insensitive() -> None:
    assert _extract_type(["FEAT"]) == TicketType.feat


def test_extract_type_defaults_to_feat_when_unknown() -> None:
    assert _extract_type(["agent-ready", "unknown-label"]) == TicketType.feat


def test_extract_type_empty_labels() -> None:
    assert _extract_type([]) == TicketType.feat


# ------------------------------------------------------------------
# Pull mode — happy path
# ------------------------------------------------------------------


async def test_pull_creates_ticket_for_new_issue(tmp_path: Path) -> None:
    issue = _make_issue()
    github_svc = AsyncMock()
    github_svc.list_agent_ready_issues.return_value = [issue]

    ticket_svc = AsyncMock()
    ticket_svc.list_tickets.return_value = []
    ticket_svc.create_ticket.return_value = _make_ticket(github_issue_url=issue.html_url)

    agent = _make_agent(github_svc, ticket_svc, project_path=tmp_path)
    result = await agent.run("pull")

    assert result.pulled == 1
    assert result.pushed == 0
    ticket_svc.create_ticket.assert_called_once()


async def test_pull_assigns_sequential_id_not_issue_number(tmp_path: Path) -> None:
    """ID should be max(existing) + 1, never issue.number directly."""
    issue = _make_issue(number=42)
    github_svc = AsyncMock()
    github_svc.list_agent_ready_issues.return_value = [issue]

    captured: list[Ticket] = []

    async def _fake_create(draft: Ticket) -> Ticket:
        captured.append(draft)
        return draft

    ticket_svc = AsyncMock()
    ticket_svc.list_tickets.return_value = []
    ticket_svc.create_ticket = _fake_create

    agent = _make_agent(github_svc, ticket_svc, project_path=tmp_path)
    await agent.run("pull")

    assert len(captured) == 1
    assert captured[0].id == "ticket-001"  # next after 0, not 042


async def test_pull_collision_free_id_with_existing_tickets(tmp_path: Path) -> None:
    """Should use max(existing) + 1 even if issue.number matches existing."""
    issue = _make_issue(number=7)  # ticket-007 would collide
    github_svc = AsyncMock()
    github_svc.list_agent_ready_issues.return_value = [issue]

    existing = _make_ticket(ticket_id="ticket-007")
    captured: list[Ticket] = []

    async def _fake_create(draft: Ticket) -> Ticket:
        captured.append(draft)
        return draft

    ticket_svc = AsyncMock()
    ticket_svc.list_tickets.return_value = [existing]
    ticket_svc.create_ticket = _fake_create

    agent = _make_agent(github_svc, ticket_svc, project_path=tmp_path)
    await agent.run("pull")

    assert len(captured) == 1
    assert captured[0].id == "ticket-008"  # 007 + 1


async def test_pull_ticket_has_correct_fields(tmp_path: Path) -> None:
    issue = _make_issue(number=5, title="Add feature", body="Details.", labels=["feat", "agent-ready"])
    github_svc = AsyncMock()
    github_svc.list_agent_ready_issues.return_value = [issue]

    captured: list[Ticket] = []

    async def _fake_create(draft: Ticket) -> Ticket:
        captured.append(draft)
        return draft

    ticket_svc = AsyncMock()
    ticket_svc.list_tickets.return_value = []
    ticket_svc.create_ticket = _fake_create

    agent = _make_agent(github_svc, ticket_svc, project_path=tmp_path)
    await agent.run("pull")

    draft = captured[0]
    assert draft.title == "Add feature"
    assert draft.type == TicketType.feat
    assert draft.status == TicketStatus.todo
    assert draft.priority == TicketPriority.medium
    assert draft.agent == "orchestrateur"
    assert draft.github_issue_url == issue.html_url
    assert draft.body == "Details."


async def test_pull_updates_github_labels(tmp_path: Path) -> None:
    issue = _make_issue(number=7)
    github_svc = AsyncMock()
    github_svc.list_agent_ready_issues.return_value = [issue]

    ticket_svc = AsyncMock()
    ticket_svc.list_tickets.return_value = []
    ticket_svc.create_ticket.return_value = _make_ticket(github_issue_url=issue.html_url)

    agent = _make_agent(github_svc, ticket_svc, project_path=tmp_path)
    await agent.run("pull")

    github_svc.remove_label.assert_called_once_with(7, "agent-ready")
    github_svc.add_label.assert_called_once_with(7, "synced-to-agent")


async def test_pull_writes_sync_log(tmp_path: Path) -> None:
    issue = _make_issue(number=3, title="Bug fix")
    github_svc = AsyncMock()
    github_svc.list_agent_ready_issues.return_value = [issue]

    ticket_svc = AsyncMock()
    ticket_svc.list_tickets.return_value = []
    ticket_svc.create_ticket.return_value = _make_ticket()

    agent = _make_agent(github_svc, ticket_svc, project_path=tmp_path)
    await agent.run("pull")

    log = (tmp_path / "memory" / "github-sync-log.md").read_text()
    assert "PULLED" in log
    assert "ticket-001" in log
    assert "#3" in log


# ------------------------------------------------------------------
# Pull mode — deduplication
# ------------------------------------------------------------------


async def test_pull_skips_already_synced_issue(tmp_path: Path) -> None:
    issue = _make_issue(html_url="https://github.com/owner/repo/issues/1")
    github_svc = AsyncMock()
    github_svc.list_agent_ready_issues.return_value = [issue]

    existing = _make_ticket(github_issue_url="https://github.com/owner/repo/issues/1")
    ticket_svc = AsyncMock()
    ticket_svc.list_tickets.return_value = [existing]

    agent = _make_agent(github_svc, ticket_svc, project_path=tmp_path)
    result = await agent.run("pull")

    assert result.pulled == 0
    assert result.skipped == 1
    ticket_svc.create_ticket.assert_not_called()


async def test_pull_skips_issue_already_in_sync_map(tmp_path: Path) -> None:
    issue = _make_issue(number=5)
    github_svc = AsyncMock()
    github_svc.list_agent_ready_issues.return_value = [issue]

    ticket_svc = AsyncMock()
    ticket_svc.list_tickets.return_value = []

    sync_map = _mock_sync_map({"ticket-001": SyncEntry(issue=5)})  # issue 5 already mapped
    agent = _make_agent(github_svc, ticket_svc, sync_map_svc=sync_map, project_path=tmp_path)
    result = await agent.run("pull")

    assert result.skipped == 1
    ticket_svc.create_ticket.assert_not_called()


async def test_pull_idempotent_on_empty_issues(tmp_path: Path) -> None:
    github_svc = AsyncMock()
    github_svc.list_agent_ready_issues.return_value = []
    ticket_svc = AsyncMock()
    ticket_svc.list_tickets.return_value = []

    agent = _make_agent(github_svc, ticket_svc, project_path=tmp_path)
    result = await agent.run("pull")

    assert result == SyncResult(pulled=0, pushed=0, skipped=0)
    ticket_svc.create_ticket.assert_not_called()


async def test_pull_processes_multiple_new_issues(tmp_path: Path) -> None:
    issues = [
        _make_issue(number=i, html_url=f"https://github.com/owner/repo/issues/{i}")
        for i in range(1, 4)
    ]
    github_svc = AsyncMock()
    github_svc.list_agent_ready_issues.return_value = issues

    ticket_svc = AsyncMock()
    ticket_svc.list_tickets.return_value = []
    ticket_svc.create_ticket.side_effect = [
        _make_ticket(github_issue_url=issue.html_url) for issue in issues
    ]

    agent = _make_agent(github_svc, ticket_svc, project_path=tmp_path)
    result = await agent.run("pull")

    assert result.pulled == 3
    assert ticket_svc.create_ticket.call_count == 3
    assert github_svc.remove_label.call_count == 3
    assert github_svc.add_label.call_count == 3


# ------------------------------------------------------------------
# Push mode
# ------------------------------------------------------------------


async def test_push_closes_existing_issue_for_done_ticket(tmp_path: Path) -> None:
    done_ticket = _make_ticket(ticket_id="ticket-001", status=TicketStatus.done)
    ticket_svc = AsyncMock()
    ticket_svc.list_tickets.return_value = [done_ticket]

    github_svc = AsyncMock()
    sync_map = _mock_sync_map({"ticket-001": SyncEntry(issue=7)})

    agent = _make_agent(github_svc, ticket_svc, sync_map_svc=sync_map, project_path=tmp_path)
    result = await agent.run("push")

    assert result.pushed == 1
    github_svc.close_issue.assert_called_once_with(7)
    github_svc.create_issue.assert_not_called()


async def test_push_creates_and_closes_issue_for_unmapped_done_ticket(tmp_path: Path) -> None:
    done_ticket = _make_ticket(ticket_id="ticket-002", status=TicketStatus.done, title="New feat")
    ticket_svc = AsyncMock()
    ticket_svc.list_tickets.return_value = [done_ticket]

    github_svc = AsyncMock()
    github_svc.create_issue.return_value = 99

    agent = _make_agent(github_svc, ticket_svc, project_path=tmp_path)
    result = await agent.run("push")

    assert result.pushed == 1
    github_svc.create_issue.assert_called_once()
    github_svc.close_issue.assert_called_once_with(99)


async def test_push_uses_label_map_when_creating_issue(tmp_path: Path) -> None:
    done_ticket = _make_ticket(
        ticket_id="ticket-003", status=TicketStatus.done,
        ticket_type=TicketType.fix, title="Bug fix"
    )
    ticket_svc = AsyncMock()
    ticket_svc.list_tickets.return_value = [done_ticket]

    github_svc = AsyncMock()
    github_svc.create_issue.return_value = 10

    agent = _make_agent(
        github_svc, ticket_svc,
        project_path=tmp_path,
        label_map={"fix": "bug"},
    )
    await agent.run("push")

    call_args = github_svc.create_issue.call_args
    assert "bug" in call_args.kwargs.get("labels", call_args.args[2] if len(call_args.args) > 2 else [])


async def test_push_no_done_tickets_returns_zero(tmp_path: Path) -> None:
    ticket_svc = AsyncMock()
    ticket_svc.list_tickets.return_value = []
    github_svc = AsyncMock()

    agent = _make_agent(github_svc, ticket_svc, project_path=tmp_path)
    result = await agent.run("push")

    assert result.pushed == 0
    github_svc.close_issue.assert_not_called()
    github_svc.create_issue.assert_not_called()


async def test_push_writes_sync_log(tmp_path: Path) -> None:
    done_ticket = _make_ticket(ticket_id="ticket-001", status=TicketStatus.done, title="Closed feat")
    ticket_svc = AsyncMock()
    ticket_svc.list_tickets.return_value = [done_ticket]

    github_svc = AsyncMock()
    sync_map = _mock_sync_map({"ticket-001": SyncEntry(issue=3)})

    agent = _make_agent(github_svc, ticket_svc, sync_map_svc=sync_map, project_path=tmp_path)
    await agent.run("push")

    log = (tmp_path / "memory" / "github-sync-log.md").read_text()
    assert "CLOSED" in log
    assert "#3" in log


# ------------------------------------------------------------------
# Both mode
# ------------------------------------------------------------------


async def test_both_mode_pulls_and_pushes(tmp_path: Path) -> None:
    issue = _make_issue(number=10, html_url="https://github.com/owner/repo/issues/10")
    done_ticket = _make_ticket(ticket_id="ticket-001", status=TicketStatus.done)

    github_svc = AsyncMock()
    github_svc.list_agent_ready_issues.return_value = [issue]
    github_svc.create_issue.return_value = 11

    ticket_svc = AsyncMock()
    # pull calls list_tickets with no status; push calls with status=done
    ticket_svc.list_tickets.side_effect = [
        [],           # pull: all tickets (no status filter)
        [done_ticket],  # push: done tickets
    ]
    ticket_svc.create_ticket.return_value = _make_ticket()

    agent = _make_agent(github_svc, ticket_svc, project_path=tmp_path)
    result = await agent.run("both")

    assert result.pulled == 1
    assert result.pushed == 1


# ------------------------------------------------------------------
# Sync map persistence
# ------------------------------------------------------------------


async def test_run_saves_sync_map_after_pull(tmp_path: Path) -> None:
    issue = _make_issue(number=5)
    github_svc = AsyncMock()
    github_svc.list_agent_ready_issues.return_value = [issue]

    ticket_svc = AsyncMock()
    ticket_svc.list_tickets.return_value = []
    ticket_svc.create_ticket.return_value = _make_ticket()

    real_sync_map = SyncMapService()
    agent = _make_agent(github_svc, ticket_svc, sync_map_svc=real_sync_map, project_path=tmp_path)
    await agent.run("pull")

    saved = real_sync_map.load(tmp_path)
    assert any(e.issue == 5 for e in saved.values())
