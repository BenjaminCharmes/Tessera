"""Actions run on an existing project: plan, analyze, GitHub sync — ticket-689."""

from fastapi import HTTPException

from tessera.agents.github_sync import GithubSyncAgent
from tessera.config import settings
from tessera.models.project import (
    AnalysisResult,
    AnalyzeProjectRequest,
    GithubSyncRequest,
    GithubSyncResult,
    PlanRequest,
    PlanResult,
)
from tessera.routers.projects.shared import loader, new_router, ticket_svc
from tessera.services.github_service import GitHubService
from tessera.services.manifeste import lire_label_map
from tessera.services.planner import PlannerService
from tessera.services.project_analyzer import ProjectAnalyzerService
from tessera.services.providers.par_role import modele_du_role, provider_pour_role
from tessera.services.sync_map import SyncMapService

router = new_router()


@router.post("/{project_id}/plan", response_model=PlanResult)
async def plan_project(project_id: str, body: PlanRequest) -> PlanResult:
    project_path = settings.ide_workspace_dir / project_id
    if not project_path.is_dir():
        raise HTTPException(status_code=404, detail=f"Projet '{project_id}' introuvable.")
    # Pure text-in/JSON-out: no filesystem tools needed (ticket-044 review, finding 4).
    provider = provider_pour_role(
        project_path, "planificateur", allow_tools=False, project_id=project_id
    )
    svc = PlannerService(
        provider, settings.ide_prompts_dir, settings.ide_workspace_dir,
        model=modele_du_role(project_path, "planificateur"),
    )
    try:
        return await svc.plan(project_id, body.description)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/{project_id}/analyze", response_model=AnalysisResult)
async def analyze_project(project_id: str, body: AnalyzeProjectRequest) -> AnalysisResult:
    project_path = settings.ide_workspace_dir / project_id
    if not project_path.is_dir():
        raise HTTPException(status_code=404, detail=f"Projet '{project_id}' introuvable.")
    # Pure text-in/JSON-out: no filesystem tools needed (ticket-044 review, finding 4).
    provider = provider_pour_role(
        project_path, "project-analyzer", allow_tools=False, project_id=project_id
    )
    svc = ProjectAnalyzerService(
        provider, settings.ide_prompts_dir,
        model=modele_du_role(project_path, "project-analyzer"),
    )
    try:
        return await svc.analyze(project_path, overwrite=body.overwrite)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/{project_id}/github/sync", response_model=GithubSyncResult)
async def github_sync(project_id: str, body: GithubSyncRequest) -> GithubSyncResult:
    project_path = settings.ide_workspace_dir / project_id
    if not project_path.is_dir():
        raise HTTPException(status_code=404, detail=f"Projet '{project_id}' introuvable.")

    project = await loader().load_project(project_id)
    if not project.github_remote:
        raise HTTPException(
            status_code=422,
            detail="Ce projet n'a pas de github_remote configuré dans agents.json.",
        )
    if not settings.github_token:
        raise HTTPException(
            status_code=422,
            detail="GITHUB_TOKEN non configuré dans les settings.",
        )

    label_map = lire_label_map(project_path)

    github_svc = GitHubService(token=settings.github_token, repo=project.github_remote)
    agent = GithubSyncAgent(
        github_svc=github_svc,
        ticket_svc=ticket_svc(project_id),
        sync_map_svc=SyncMapService(),
        project_path=project_path,
        label_map=label_map,
    )

    sync_result = await agent.run(direction=body.direction)
    return GithubSyncResult(
        pulled=sync_result.pulled,
        pushed=sync_result.pushed,
        skipped=sync_result.skipped,
    )
