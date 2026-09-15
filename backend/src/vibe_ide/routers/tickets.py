from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from vibe_ide.config import settings
from vibe_ide.models.ticket import Ticket, TicketBatchCreate, TicketBatchResponse, TicketCreate, TicketStatus, TicketStatusUpdate
from vibe_ide.services.github_service import GitHubService, PRStatus
from vibe_ide.services.project_loader import ProjectLoader
from vibe_ide.services.sync_map import SyncMapService
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


# Note : /batch et /archive DOIVENT être définis avant /{ticket_id} pour éviter les collisions
@router.post("/{project_id}/tickets/batch", response_model=TicketBatchResponse, status_code=201)
async def create_tickets_batch(project_id: str, body: TicketBatchCreate) -> TicketBatchResponse:
    created = await _svc(project_id).create_tickets_batch(body.tickets)
    return TicketBatchResponse(created=created)


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


# ------------------------------------------------------------------
# PR endpoints — must come after /{ticket_id} to avoid collisions
# FastAPI resolves them correctly since /create-pr and /pr-status
# are literal path segments.
# ------------------------------------------------------------------


class CreatePrRequest(BaseModel):
    head_branch: str
    base: str | None = None  # None -> settings.github_base_branch (develop)


class CreatePrResponse(BaseModel):
    pr_number: int
    pr_url: str


class PrStatusResponse(BaseModel):
    state: Literal["open", "closed", "merged"]
    ci_status: Literal["pending", "passing", "failing", "none"]
    pr_url: str
    pr_number: int


def _require_github_service(github_remote: str | None) -> GitHubService:
    if not github_remote:
        raise HTTPException(
            status_code=422,
            detail="Ce projet n'a pas de github_remote configuré dans agents.json.",
        )
    if not settings.github_token:
        raise HTTPException(
            status_code=422,
            detail="GITHUB_TOKEN non configuré dans les settings.",
        )
    return GitHubService(token=settings.github_token, repo=github_remote)


@router.post("/{project_id}/tickets/{ticket_id}/create-pr", response_model=CreatePrResponse, status_code=201)
async def create_pull_request(
    project_id: str, ticket_id: str, body: CreatePrRequest
) -> CreatePrResponse:
    loader = ProjectLoader(settings.ide_workspace_dir)
    try:
        project = await loader.load_project(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    github_svc = _require_github_service(project.github_remote)
    ticket_svc = _svc(project_id)

    ticket = await ticket_svc.get_ticket(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} introuvable")

    if ticket.pr_number is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Une PR #{ticket.pr_number} existe déjà pour ce ticket.",
        )

    pr_number, pr_url = await github_svc.create_pull_request(
        title=ticket.title,
        body=ticket.body or "",
        head=body.head_branch,
        base=body.base,
    )

    await ticket_svc.set_pr_number(ticket_id, pr_number)

    project_path = settings.ide_workspace_dir / project_id
    sync_map_svc = SyncMapService()
    mapping = sync_map_svc.load(project_path)
    updated = sync_map_svc.set_pr(mapping, ticket_id, pr_number)
    sync_map_svc.save(project_path, updated)

    return CreatePrResponse(pr_number=pr_number, pr_url=pr_url)


@router.get("/{project_id}/tickets/{ticket_id}/pr-status", response_model=PrStatusResponse)
async def get_pr_status(project_id: str, ticket_id: str) -> PrStatusResponse:
    loader = ProjectLoader(settings.ide_workspace_dir)
    try:
        project = await loader.load_project(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    github_svc = _require_github_service(project.github_remote)
    ticket_svc = _svc(project_id)

    ticket = await ticket_svc.get_ticket(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} introuvable")

    if ticket.pr_number is None:
        raise HTTPException(
            status_code=404,
            detail=f"Aucune PR associée au ticket {ticket_id}.",
        )

    status: PRStatus = await github_svc.get_pull_request_status(ticket.pr_number)
    return PrStatusResponse(
        state=status.state,
        ci_status=status.ci_status,
        pr_url=status.pr_url,
        pr_number=status.pr_number,
    )
