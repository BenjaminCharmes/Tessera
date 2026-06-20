from fastapi import APIRouter, HTTPException

from vibe_ide.config import settings
from vibe_ide.models.ticket import Ticket, TicketCreate, TicketStatus, TicketStatusUpdate
from vibe_ide.services.ticket_service import TicketService

router = APIRouter(tags=["tickets"])


def _svc(project_id: str) -> TicketService:
    return TicketService(settings.ide_workspace_dir / project_id, project_id)


@router.get("/{project_id}/tickets", response_model=list[Ticket])
async def list_tickets(
    project_id: str, status: str | None = None
) -> list[Ticket]:
    from vibe_ide.models.ticket import TicketStatus

    filter_status = TicketStatus(status) if status else None
    return await _svc(project_id).list_tickets(filter_status)


@router.post("/{project_id}/tickets", response_model=Ticket, status_code=201)
async def create_ticket(project_id: str, body: TicketCreate) -> Ticket:
    ticket = Ticket(
        id="",
        title=body.title,
        type=body.type,
        status=TicketStatus.todo,
        priority=body.priority,
        agent=body.agent,
        depends_on=body.depends_on,
        body=body.description,
    )
    return await _svc(project_id).create_ticket(ticket)


# Note : /archive DOIT être défini avant /{ticket_id} pour éviter la collision de routes
@router.get("/{project_id}/tickets/archive", response_model=list[Ticket])
async def list_archived_tickets(project_id: str) -> list[Ticket]:
    return await _svc(project_id).list_archived_tickets()


@router.get("/{project_id}/tickets/{ticket_id}", response_model=Ticket)
async def get_ticket(project_id: str, ticket_id: str) -> Ticket:
    ticket = await _svc(project_id).get_ticket(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} introuvable")
    return ticket


@router.patch("/{project_id}/tickets/{ticket_id}", response_model=Ticket)
async def update_ticket_status(
    project_id: str, ticket_id: str, body: TicketStatusUpdate
) -> Ticket:
    try:
        return await _svc(project_id).update_status(ticket_id, body.status)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
