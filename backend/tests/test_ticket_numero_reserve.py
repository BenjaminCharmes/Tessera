"""A ticket created without id takes its number through the reservation — ticket-1042."""
import json
from pathlib import Path

from tessera.config import settings
from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services.noyau import numerotation, reservation
from tessera.services.projets.ticket_service import TicketService


def _projet(tmp_path: Path, dernier: int) -> Path:
    todo = tmp_path / "projet" / "tickets" / "todo"
    todo.mkdir(parents=True)
    (todo / f"ticket-{dernier:03d}-x.md").write_text("x", encoding="utf-8")
    return tmp_path / "projet"


def _sans_id() -> Ticket:
    return Ticket(
        id="",
        title="Sans identifiant",
        type=TicketType.feat,
        status=TicketStatus.todo,
        priority=TicketPriority.medium,
        agent="codeur",
    )


def test_ticket_skips_a_number_reserved_by_the_script(tmp_path: Path) -> None:
    projet = _projet(tmp_path, 9)
    reserve = numerotation.reserver(projet, "ticket", "develop", settings.ide_state_dir)
    assert reserve == 10

    cree = TicketService(projet, "p").create_ticket_sync(_sans_id())

    assert cree.id == "ticket-011"


def test_two_tickets_get_two_numbers_and_the_file_holds_the_second(tmp_path: Path) -> None:
    projet = _projet(tmp_path, 4)
    service = TicketService(projet, "p")

    premier = service.create_ticket_sync(_sans_id())
    second = service.create_ticket_sync(_sans_id())

    assert (premier.id, second.id) == ("ticket-005", "ticket-006")
    contenu = json.loads(
        (settings.ide_state_dir / reservation.NOM_FICHIER).read_text(encoding="utf-8")
    )
    assert [genres["ticket"] for genres in contenu.values()] == [6]


def test_folder_outside_any_git_repository_uses_the_tree(tmp_path: Path) -> None:
    projet = _projet(tmp_path, 41)

    cree = TicketService(projet, "p").create_ticket_sync(_sans_id())

    assert cree.id == "ticket-042"
