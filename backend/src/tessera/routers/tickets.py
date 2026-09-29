from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from tessera.config import settings
from tessera.services.ticket_diff import TicketDiff, diff_du_ticket
from tessera.models.ticket import Ticket, TicketBatchCreate, TicketBatchResponse, TicketCreate, TicketListResponse, TicketStatus, TicketStatusUpdate
from tessera.services.github_service import GitHubService, PRStatus
from tessera.services.autonomie import lire_niveau
from tessera.services.database import list_runs
from tessera.services.event_hub import EVENT_HUB
from tessera.services.pipeline_events import EventType, OrchestratorEvent
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)
from tessera.services.git_workspace import GitWorkspaceError, GitWorkspaceService
from tessera.services.github_workflow import GitHubWorkflowService, WorkflowError
from tessera.services.project_loader import load_project
from tessera.services.project_loader import ProjectLoader
from tessera.services.sync_map import SyncMapService
from tessera.services.ticket_service import TicketService

router = APIRouter(tags=["tickets"])


def _svc(project_id: str) -> TicketService:
    return TicketService(settings.ide_workspace_dir / project_id, project_id)


@router.get("/{project_id}/tickets", response_model=TicketListResponse)
async def list_tickets(
    project_id: str, status: str | None = None
) -> TicketListResponse:
    filter_status = _parse_status_filter(status)
    tickets, unreadable = await _svc(project_id).list_tickets_with_unreadable(filter_status)
    return TicketListResponse(tickets=tickets, unreadable=unreadable)


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
        ticket = await _svc(project_id).update_status(ticket_id, body.status)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    # Le même événement que le pipeline : la liste et le Kanban de chaque
    # onglet se mettent à jour sans recharger (ticket-194). Un émetteur qui
    # lève n'annule pas un statut déjà écrit sur disque (ADR-038).
    try:
        await EVENT_HUB.publish(
            OrchestratorEvent(
                type=EventType.TICKET_STATUS_CHANGED,
                ticket_id=ticket_id,
                project_id=project_id,
                data={"status": body.status.value, "manuel": True},
            )
        )
    except Exception as exc:  # noqa: BLE001
        _logger.warning("status_event_emit_failed", extra={"error": str(exc)})
    return ticket


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

    try:
        status: PRStatus = await github_svc.get_pull_request_status(ticket.pr_number)
    except httpx.HTTPStatusError as exc:
        # Un pr_number hérité d'un autre dépôt n'existe pas ici : c'est un
        # 404 définitif, pas une panne. En 500, la carte réessayait toutes les
        # 30 s et brûlait le quota GitHub (ticket-217).
        if exc.response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail=f"PR #{ticket.pr_number} introuvable dans {project.github_remote}.",
            ) from exc
        raise
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
    #: La cause d'un blocage, quand il y en a eu une (ticket-218).
    arret: str | None = None


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
    #: Jusqu'où ce projet laisse l'IDE aller seul : `commit`, `pr` ou `merge`
    #: (ticket-082). Sans cela, rien à l'écran n'explique pourquoi l'IDE
    #: s'arrête après le commit ici et va jusqu'au merge ailleurs.
    autonomy: str = "commit"


class MergeResponse(BaseModel):
    pr_number: int
    merged: bool


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
            arret=row.get("arret"),
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
    forge = getattr(project, "github_forge", None)
    return TicketActivity(
        ticket_id=ticket_id,
        runs=runs,
        pr_supported=forge == "GitHub",
        forge=forge,
        pr_number=ticket.pr_number,
        github_remote=remote,
        autonomy=lire_niveau(project_path).value,
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
        project_path=project_path,
    )

    try:
        result = await service.open_pull_request(
            branch=body.branch,
            ticket_id=ticket_id,
            ticket_title=ticket.title,
            ticket_body=ticket.body or "",
            # C'est l'utilisateur qui vient de cliquer. Le niveau d'autonomie
            # borne ce que l'IDE fait seul, pas ce qu'on peut lui demander.
            autonome=False,
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


@router.post("/{project_id}/tickets/{ticket_id}/merge-pr", response_model=MergeResponse)
async def merge_pull_request_for_ticket(
    project_id: str, ticket_id: str
) -> MergeResponse:
    """Merge la PR du ticket, **si** le projet l'a déclaré et si la CI est verte.

    Les deux conditions se vérifient au moment d'agir (ADR-029). Un refus n'est
    pas une panne : c'est le cas normal partout où l'utilisateur garde la main.
    """
    ticket_svc = _svc(project_id)
    ticket = await ticket_svc.get_ticket(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} introuvable")
    if ticket.pr_number is None:
        raise HTTPException(
            status_code=422, detail="Ce ticket n'a pas de pull request ouverte."
        )

    project_path = settings.ide_workspace_dir / project_id
    project = load_project(project_path)
    github = None
    if project.github_remote and settings.github_token:
        github = GitHubService(token=settings.github_token, repo=project.github_remote)

    service = GitHubWorkflowService(
        git_workspace=GitWorkspaceService(project_path),
        github=github,
        base_branch=settings.github_base_branch,
        project_path=project_path,
    )

    merge = await service.merge_si_la_ci_est_verte(ticket.pr_number)
    if not merge:
        raise HTTPException(
            status_code=422,
            detail=(
                "Merge refusé : il faut que ce projet déclare "
                '`"autonomy": "merge"` et que la CI de la PR soit verte.'
            ),
        )
    return MergeResponse(pr_number=ticket.pr_number, merged=True)
