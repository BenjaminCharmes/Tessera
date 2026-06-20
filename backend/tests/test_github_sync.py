from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from vibe_ide.agents.github_sync import GithubSyncAgent, _extract_type
from vibe_ide.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from vibe_ide.services.github_service import GitHubIssue


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
    github_issue_url: str | None = None,
    status: TicketStatus = TicketStatus.todo,
) -> Ticket:
    return Ticket(
        id="ticket-001",
        title="Some ticket",
        type=TicketType.feat,
        status=status,
        priority=TicketPriority.medium,
        agent="codeur",
        github_issue_url=github_issue_url,
    )


def _make_agent(
    github_svc: MagicMock | None = None,
    ticket_svc: MagicMock | None = None,
) -> GithubSyncAgent:
    return GithubSyncAgent(
        github_svc=github_svc or MagicMock(),
        ticket_svc=ticket_svc or MagicMock(),
    )


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
# GithubSyncAgent.run — happy path
# ------------------------------------------------------------------


async def test_run_creates_ticket_for_new_issue() -> None:
    issue = _make_issue()
    github_svc = AsyncMock()
    github_svc.list_agent_ready_issues.return_value = [issue]

    created_ticket = _make_ticket(github_issue_url=issue.html_url)
    ticket_svc = AsyncMock()
    ticket_svc.list_tickets.return_value = []
    ticket_svc.create_ticket.return_value = created_ticket

    agent = _make_agent(github_svc, ticket_svc)
    result = await agent.run()

    assert len(result) == 1
    assert result[0].github_issue_url == issue.html_url
    ticket_svc.create_ticket.assert_called_once()


async def test_run_ticket_has_correct_fields() -> None:
    issue = _make_issue(number=42, title="Fix login", body="Steps to reproduce.", labels=["fix", "agent-ready"])
    github_svc = AsyncMock()
    github_svc.list_agent_ready_issues.return_value = [issue]

    captured_draft: list[Ticket] = []

    async def _fake_create(draft: Ticket) -> Ticket:
        captured_draft.append(draft)
        return draft

    ticket_svc = AsyncMock()
    ticket_svc.list_tickets.return_value = []
    ticket_svc.create_ticket = _fake_create

    agent = _make_agent(github_svc, ticket_svc)
    await agent.run()

    assert len(captured_draft) == 1
    draft = captured_draft[0]
    assert draft.id == "ticket-042"
    assert draft.title == "Fix login"
    assert draft.type == TicketType.fix
    assert draft.status == TicketStatus.todo
    assert draft.priority == TicketPriority.medium
    assert draft.agent == "orchestrateur"
    assert draft.github_issue_url == issue.html_url
    assert draft.body == "Steps to reproduce."


async def test_run_updates_github_labels() -> None:
    issue = _make_issue(number=7)
    github_svc = AsyncMock()
    github_svc.list_agent_ready_issues.return_value = [issue]

    ticket_svc = AsyncMock()
    ticket_svc.list_tickets.return_value = []
    ticket_svc.create_ticket.return_value = _make_ticket(github_issue_url=issue.html_url)

    agent = _make_agent(github_svc, ticket_svc)
    await agent.run()

    github_svc.remove_label.assert_called_once_with(7, "agent-ready")
    github_svc.add_label.assert_called_once_with(7, "synced-to-agent")


# ------------------------------------------------------------------
# GithubSyncAgent.run — deduplication
# ------------------------------------------------------------------


async def test_run_skips_already_synced_issue() -> None:
    issue = _make_issue(html_url="https://github.com/owner/repo/issues/1")
    github_svc = AsyncMock()
    github_svc.list_agent_ready_issues.return_value = [issue]

    existing = _make_ticket(github_issue_url="https://github.com/owner/repo/issues/1")
    ticket_svc = AsyncMock()
    ticket_svc.list_tickets.return_value = [existing]

    agent = _make_agent(github_svc, ticket_svc)
    result = await agent.run()

    assert result == []
    ticket_svc.create_ticket.assert_not_called()
    github_svc.remove_label.assert_not_called()
    github_svc.add_label.assert_not_called()


async def test_run_skips_only_duplicate_creates_new() -> None:
    issue_dup = _make_issue(number=1, html_url="https://github.com/owner/repo/issues/1")
    issue_new = _make_issue(number=2, html_url="https://github.com/owner/repo/issues/2")
    github_svc = AsyncMock()
    github_svc.list_agent_ready_issues.return_value = [issue_dup, issue_new]

    existing = _make_ticket(github_issue_url="https://github.com/owner/repo/issues/1")
    new_ticket = _make_ticket(github_issue_url="https://github.com/owner/repo/issues/2")
    ticket_svc = AsyncMock()
    ticket_svc.list_tickets.return_value = [existing]
    ticket_svc.create_ticket.return_value = new_ticket

    agent = _make_agent(github_svc, ticket_svc)
    result = await agent.run()

    assert len(result) == 1
    assert result[0].github_issue_url == "https://github.com/owner/repo/issues/2"
    ticket_svc.create_ticket.assert_called_once()


async def test_run_idempotent_on_empty_issues() -> None:
    github_svc = AsyncMock()
    github_svc.list_agent_ready_issues.return_value = []
    ticket_svc = AsyncMock()
    ticket_svc.list_tickets.return_value = []

    agent = _make_agent(github_svc, ticket_svc)
    result = await agent.run()

    assert result == []
    ticket_svc.create_ticket.assert_not_called()


async def test_run_processes_multiple_new_issues() -> None:
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

    agent = _make_agent(github_svc, ticket_svc)
    result = await agent.run()

    assert len(result) == 3
    assert ticket_svc.create_ticket.call_count == 3
    assert github_svc.remove_label.call_count == 3
    assert github_svc.add_label.call_count == 3
