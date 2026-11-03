"""Archiving of done tickets — ticket-660."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from tessera.config import settings
from tessera.routers.dependencies import require_valid_project_id
from tessera.services.ticket_service import TicketService

router = APIRouter(
    tags=["tickets"],
    dependencies=[Depends(require_valid_project_id)],
)


class ArchiveResponse(BaseModel):
    archived: list[str]


@router.post("/{project_id}/tickets/archive", response_model=ArchiveResponse)
async def archive_tickets(project_id: str) -> ArchiveResponse:
    """Archive the done tickets numbered 100+ below the project's highest."""
    service = TicketService(settings.ide_workspace_dir / project_id, project_id)
    return ArchiveResponse(archived=await service.archive_done_tickets())
