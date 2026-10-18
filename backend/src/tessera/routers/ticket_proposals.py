"""Proposer des tickets à un projet pendant qu'un run occupe son arbre — ticket-479.

Ni `RunLock` ni `RUN_REGISTRY` ici : la route sert précisément quand un run
tient le projet, et elle n'écrit jamais dans son arbre de travail.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from tessera.config import settings
from tessera.routers.dependencies import require_valid_project_id
from tessera.routers.tickets import _require_github_service
from tessera.services.git_workspace import GitWorkspaceError
from tessera.services.github_workflow import WorkflowError
from tessera.services.politique_run import PolitiqueRun
from tessera.services.project_loader import ProjectLoader
from tessera.services.ticket_proposal import (
    ProposalRefused,
    ProposalRequest,
    propose_tickets,
    validate_batch,
)

router = APIRouter(
    tags=["tickets"],
    dependencies=[Depends(require_valid_project_id)],
)


class ProposedTicketFile(BaseModel):
    name: str
    content: str


class TicketProposal(BaseModel):
    tickets: list[ProposedTicketFile] = Field(min_length=1)


class TicketProposalResponse(BaseModel):
    branch: str
    pr_number: int
    pr_url: str
    ticket_ids: list[str]
    #: Vrai quand le merge est confié au suivi de CI (`autonomy: merge`) ;
    #: faux, la PR reste ouverte.
    merge_watched: bool


@router.post(
    "/{project_id}/tickets/propose",
    response_model=TicketProposalResponse,
    status_code=201,
)
async def propose_tickets_to_project(
    project_id: str, body: TicketProposal
) -> TicketProposalResponse:
    """Dépose les tickets dans une PR vers la base, sans toucher à l'arbre du projet."""
    try:
        project = await ProjectLoader(settings.ide_workspace_dir).load_project(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    files = tuple((t.name, t.content) for t in body.tickets)
    # Le lot d'abord : un ticket invalide reçoit son 422 de frontmatter,
    # pas l'erreur de configuration GitHub.
    try:
        validate_batch(files)
    except ProposalRefused as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    github = _require_github_service(project.github_remote)
    project_path = settings.ide_workspace_dir / project_id
    policy = PolitiqueRun.lire(project_path)
    request = ProposalRequest(
        project_id=project_id,
        project_path=project_path,
        files=files,
        policy=policy,
        github=github,
        base_branch=policy.base_branch or settings.github_base_branch,
    )
    try:
        proposal = await propose_tickets(request)
    except (ProposalRefused, WorkflowError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except GitWorkspaceError as exc:
        raise HTTPException(
            status_code=502, detail=f"Opération git échouée : {exc}"
        ) from exc
    return TicketProposalResponse(
        branch=proposal.branch,
        pr_number=proposal.pr_number,
        pr_url=proposal.pr_url,
        ticket_ids=list(proposal.ticket_ids),
        merge_watched=proposal.merge_watched,
    )
