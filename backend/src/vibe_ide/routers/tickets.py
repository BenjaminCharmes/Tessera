from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from vibe_ide.config import settings
from vibe_ide.services.github_workflow import forge_supportee, nom_de_la_forge
from vibe_ide.services.ticket_diff import TicketDiff, diff_du_ticket
from vibe_ide.models.ticket import Ticket, TicketBatchCreate, TicketBatchResponse, TicketCreate, TicketStatus, TicketStatusUpdate
from vibe_ide.services.github_service import GitHubService, PRStatus
from vibe_ide.services.database import list_runs
from vibe_ide.services.git_workspace import GitWorkspaceError, GitWorkspaceService
from vibe_ide.services.github_workflow import GitHubWorkflowService, WorkflowError
from vibe_ide.services.project_loader import load_project
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
    filter_status = _parse_status_filter(status)
    return await _svc(project_id).list_tickets(filter_status)


def _parse_status_filter(status: str | None) -> TicketStatus | None:
    """Traduit le paramètre `status` en enum, ou refuse lisiblement.

    `TicketStatus(status)` lève un `ValueError` non capturé sur une valeur
    inconnue : l'utilisateur recevait un 500 opaque là où une faute de frappe
    dans l'URL devrait produire un refus qui nomme les valeurs acceptées
    (ticket-053).
    """
    if not status:
        return None
    try:
        return TicketStatus(status)
    except ValueError as exc:
        valid = ", ".join(s.value for s in TicketStatus)
        raise HTTPException(
            status_code=422,
            detail=f"Statut inconnu : '{status}'. Valeurs acceptées : {valid}.",
        ) from exc


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


# ------------------------------------------------------------------
# Suivi d'un ticket et ouverture de PR — ticket-064
# ------------------------------------------------------------------


class TicketRunSummary(BaseModel):
    id: str
    started_at: str
    finished_at: str | None = None
    rounds: int | None = None
    approved: bool | None = None
    final_status: str | None = None
    total_cost_usd: float = 0.0


class TicketActivity(BaseModel):
    """Ce qu'un ticket a produit, rassemblé en un endroit.

    L'information existait, éparpillée entre la base, le ticket et GitHub : il
    fallait sortir de l'IDE et lire `git log` pour savoir ce qu'un ticket
    avait réellement changé.
    """

    ticket_id: str
    runs: list[TicketRunSummary] = []
    #: L'IDE sait-il ouvrir une PR sur ce dépôt ? Faux ailleurs que sur GitHub
    #: — et le bouton poussait la branche avant d'échouer (ticket-081).
    pr_supported: bool = False
    #: Le nom de l'hébergeur, pour le dire à l'utilisateur.
    forge: str | None = None
    pr_number: int | None = None
    github_remote: str | None = None


class OpenPrRequest(BaseModel):
    branch: str


class OpenPrResponse(BaseModel):
    pr_number: int
    pr_url: str
    branch: str


@router.get("/{project_id}/tickets/{ticket_id}/diff", response_model=TicketDiff)
async def get_ticket_diff(project_id: str, ticket_id: str) -> TicketDiff:
    """Le diff produit par le run de ce ticket, tel qu'il est dans le dépôt.

    Sans cet endpoint, juger un run demandait d'ouvrir VSCode : le pipeline
    relit le diff réel depuis ADR-018, mais rien ne l'exposait (ticket-069).
    """
    ticket = await _svc(project_id).get_ticket(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} introuvable")

    return await diff_du_ticket(settings.ide_workspace_dir / project_id, ticket_id)


@router.get("/{project_id}/tickets/{ticket_id}/activity", response_model=TicketActivity)
async def get_ticket_activity(project_id: str, ticket_id: str) -> TicketActivity:
    ticket = await _svc(project_id).get_ticket(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} introuvable")

    project_path = settings.ide_workspace_dir / project_id
    rows = await list_runs(settings.ide_db_path, project_id, limit=50)
    runs = [
        TicketRunSummary(
            id=str(row["id"]),
            started_at=str(row["started_at"]),
            finished_at=row.get("finished_at"),
            rounds=row.get("rounds"),
            approved=bool(row["approved"]) if row.get("approved") is not None else None,
            final_status=row.get("final_status"),
            total_cost_usd=float(row.get("total_cost_usd") or 0.0),
        )
        for row in rows
        if row.get("ticket_id") == ticket_id
    ]

    project = None
    try:
        project = load_project(project_path)
    except Exception:  # noqa: BLE001 — un projet illisible ne doit pas casser le suivi
        project = None

    remote = getattr(project, "github_remote", None)
    return TicketActivity(
        ticket_id=ticket_id,
        runs=runs,
        pr_supported=forge_supportee(remote),
        forge=nom_de_la_forge(remote),
        pr_number=ticket.pr_number,
        github_remote=remote,
    )


@router.post("/{project_id}/tickets/{ticket_id}/open-pr", response_model=OpenPrResponse)
async def open_pull_request_for_ticket(
    project_id: str, ticket_id: str, body: OpenPrRequest
) -> OpenPrResponse:
    """Pousse la branche du ticket **puis** ouvre sa PR.

    L'ordre est le correctif : `create-pr` demandait jusqu'ici à GitHub une
    branche `head` que rien n'avait jamais poussée.

    Aucun merge : c'est le seul point où un humain tranche.
    """
    ticket_svc = _svc(project_id)
    ticket = await ticket_svc.get_ticket(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} introuvable")

    project_path = settings.ide_workspace_dir / project_id
    project = load_project(project_path)
    github = None
    if project.github_remote and settings.github_token:
        github = GitHubService(token=settings.github_token, repo=project.github_remote)

    service = GitHubWorkflowService(
        git_workspace=GitWorkspaceService(project_path),
        github=github,
        base_branch=settings.github_base_branch,
    )

    try:
        result = await service.open_pull_request(
            branch=body.branch,
            ticket_id=ticket_id,
            ticket_title=ticket.title,
            ticket_body=ticket.body or "",
        )
    except WorkflowError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except GitWorkspaceError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Le push de la branche a échoué : {exc}",
        ) from exc

    await ticket_svc.set_pr_number(ticket_id, result.pr_number)
    return OpenPrResponse(
        pr_number=result.pr_number, pr_url=result.pr_url, branch=result.branch
    )
