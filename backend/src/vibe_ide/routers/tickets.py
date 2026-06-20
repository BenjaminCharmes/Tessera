from fastapi import APIRouter

from vibe_ide.models.ticket import Ticket

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.get("", response_model=list[Ticket])
async def list_tickets() -> list[Ticket]:
    return []


@router.patch("/{ticket_id}", response_model=Ticket)
async def update_ticket(ticket_id: str, ticket: Ticket) -> Ticket:
    return ticket
