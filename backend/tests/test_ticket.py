import pytest

from vibe_ide.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType


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


def test_ticket_with_dependencies() -> None:
    t = _make_ticket(depends_on=["ticket-001", "ticket-002"])
    assert len(t.depends_on) == 2


def test_ticket_status_values() -> None:
    assert TicketStatus.todo.value == "todo"
    assert TicketStatus.in_progress.value == "in-progress"
    assert TicketStatus.done.value == "done"


def test_ticket_immutable_copy() -> None:
    t = _make_ticket()
    updated = t.model_copy(update={"status": TicketStatus.done})
    assert t.status == TicketStatus.todo
    assert updated.status == TicketStatus.done
