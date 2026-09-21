from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType


def _make_ticket(**kwargs: object) -> Ticket:
    defaults: dict[str, object] = {
        "id": "ticket-000",
        "title": "Test ticket",
        "type": TicketType.chore,
        "status": TicketStatus.todo,
        "priority": TicketPriority.medium,
        "agent": "codeur",
    }
    return Ticket(**(defaults | kwargs))


def test_ticket_creation() -> None:
    t = _make_ticket()
    assert t.id == "ticket-000"
    assert t.status == TicketStatus.todo
    assert t.depends_on == []
    assert t.created == ""
    assert t.project_id == ""
    assert t.file_path == ""


def test_ticket_with_dependencies() -> None:
    t = _make_ticket(depends_on=["ticket-001", "ticket-002"])
    assert len(t.depends_on) == 2


def test_ticket_status_values() -> None:
    assert TicketStatus.todo.value == "todo"
    assert TicketStatus.in_progress.value == "in-progress"
    assert TicketStatus.in_review.value == "in-review"
    assert TicketStatus.done.value == "done"
    assert TicketStatus.blocked.value == "blocked"


def test_ticket_immutable_copy() -> None:
    t = _make_ticket()
    updated = t.model_copy(update={"status": TicketStatus.done})
    assert t.status == TicketStatus.todo
    assert updated.status == TicketStatus.done


def test_ticket_github_issue_url_optional() -> None:
    t = _make_ticket()
    assert t.github_issue_url is None


def test_ticket_github_issue_url_set() -> None:
    url = "https://github.com/org/repo/issues/42"
    t = _make_ticket(github_issue_url=url)
    assert t.github_issue_url == url


def test_ticket_full_fields() -> None:
    t = _make_ticket(
        created="2025-06-01",
        project_id="ide-core",
        file_path="/tmp/tickets/todo/ticket-000-test.md",
    )
    assert t.created == "2025-06-01"
    assert t.project_id == "ide-core"
    assert t.file_path == "/tmp/tickets/todo/ticket-000-test.md"
