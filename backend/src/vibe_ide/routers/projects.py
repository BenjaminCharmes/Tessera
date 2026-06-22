from fastapi import APIRouter, HTTPException, Query

from anthropic import AsyncAnthropic

from vibe_ide.config import settings
from vibe_ide.models.project import (
    AnalysisResult,
    AnalyzeProjectRequest,
    CloneProjectRequest,
    CloneProjectResponse,
    GithubSyncRequest,
    GithubSyncResult,
    PlanRequest,
    PlanResult,
    Project,
    ProjectContext,
    ProjectCreate,
    ProjectCreationResult,
    ProjectImport,
    ProjectImportResponse,
)
from vibe_ide.models.ticket import TicketStatus
from vibe_ide.services.database import PipelineRunSummary, list_runs
from vibe_ide.agents.github_sync import GithubSyncAgent
from vibe_ide.services.git_clone import CloneError, GitCloneService
from vibe_ide.services.github_service import GitHubService
from vibe_ide.services.planner import PlannerService
from vibe_ide.services.project_analyzer import ProjectAnalyzerService
from vibe_ide.services.project_importer import ImportError, ProjectImporter
from vibe_ide.services.project_creator import ProjectCreatorService
from vibe_ide.services.project_loader import ProjectLoader, load_agents_config
from vibe_ide.services.sync_map import SyncMapService
from vibe_ide.services.ticket_service import TicketService

router = APIRouter(prefix="/projects", tags=["projects"])

_OPEN_STATUSES = {TicketStatus.todo, TicketStatus.in_progress, TicketStatus.in_review, TicketStatus.blocked}


def _loader() -> ProjectLoader:
    return ProjectLoader(settings.ide_workspace_dir)


def _ticket_svc(project_id: str) -> TicketService:
    return TicketService(settings.ide_workspace_dir / project_id, project_id)


@router.get("", response_model=list[Project])
async def list_projects() -> list[Project]:
    return await _loader().list_projects()


@router.post("", response_model=ProjectCreationResult, status_code=201)
async def create_project(body: ProjectCreate) -> ProjectCreationResult:
    try:
        project = await _loader().create_project(body)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    svc = ProjectCreatorService(client, settings.ide_prompts_dir, settings.ide_workspace_dir)
    agents_created = await svc._auto_create_missing_agents(
        roles=body.active_agents,
        project_name=project.name,
        project_description=project.description,
    )
    return ProjectCreationResult(project=project, agents_created=agents_created)


@router.post("/import", response_model=ProjectImportResponse, status_code=201)
async def import_project(body: ProjectImport) -> ProjectImportResponse:
    importer = ProjectImporter(settings.ide_workspace_dir)
    try:
        project = await importer.import_project(
            source_path=body.source_path,
            mode=body.mode,
            project_id=body.project_id,
        )
    except ImportError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ProjectImportResponse(project=project)


@router.post("/clone", response_model=CloneProjectResponse, status_code=201)
async def clone_project(body: CloneProjectRequest) -> CloneProjectResponse:
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    analyzer = ProjectAnalyzerService(client, settings.ide_prompts_dir)
    svc = GitCloneService(settings.ide_workspace_dir, analyzer)
    try:
        return await svc.clone(
            repo_url=body.repo_url,
            project_id=body.project_id,
        )
    except CloneError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# Note : les routes avec sous-chemin spécifique doivent être avant /{project_id}
@router.get("/{project_id}/runs", response_model=list[PipelineRunSummary])
async def list_project_runs(
    project_id: str,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[PipelineRunSummary]:
    rows = await list_runs(settings.ide_db_path, project_id, limit)
    return [PipelineRunSummary(**row) for row in rows]


@router.get("/{project_id}/context", response_model=ProjectContext)
async def get_project_context(project_id: str) -> ProjectContext:
    try:
        project = await _loader().load_project(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    project_path = settings.ide_workspace_dir / project_id
    all_tickets = await _ticket_svc(project_id).list_tickets()
    open_tickets = [t for t in all_tickets if t.status in _OPEN_STATUSES]

    decisions_path = project_path / "memory" / "decisions.md"
    recent_decisions = (
        decisions_path.read_text(encoding="utf-8") if decisions_path.exists() else ""
    )

    return ProjectContext(
        project_id=project_id,
        claude_md=project.raw_claude_md,
        active_agents=project.active_agents,
        agent_configs=load_agents_config(project_path),
        open_tickets=open_tickets,
        recent_decisions=recent_decisions,
    )


@router.post("/{project_id}/plan", response_model=PlanResult)
async def plan_project(project_id: str, body: PlanRequest) -> PlanResult:
    project_path = settings.ide_workspace_dir / project_id
    if not project_path.is_dir():
        raise HTTPException(status_code=404, detail=f"Projet '{project_id}' introuvable.")
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    svc = PlannerService(client, settings.ide_prompts_dir, settings.ide_workspace_dir)
    try:
        return await svc.plan(project_id, body.description)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/{project_id}/analyze", response_model=AnalysisResult)
async def analyze_project(project_id: str, body: AnalyzeProjectRequest) -> AnalysisResult:
    project_path = settings.ide_workspace_dir / project_id
    if not project_path.is_dir():
        raise HTTPException(status_code=404, detail=f"Projet '{project_id}' introuvable.")
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    svc = ProjectAnalyzerService(client, settings.ide_prompts_dir)
    try:
        return await svc.analyze(project_path, overwrite=body.overwrite)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/{project_id}/github/sync", response_model=GithubSyncResult)
async def github_sync(project_id: str, body: GithubSyncRequest) -> GithubSyncResult:
    project_path = settings.ide_workspace_dir / project_id
    if not project_path.is_dir():
        raise HTTPException(status_code=404, detail=f"Projet '{project_id}' introuvable.")

    project = await _loader().load_project(project_id)
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

    import json as _json
    agents_json_path = project_path / "agents.json"
    label_map: dict[str, str] = {}
    if agents_json_path.exists():
        try:
            data = _json.loads(agents_json_path.read_text(encoding="utf-8"))
            label_map = data.get("github_sync", {}).get("label_map", {})
        except Exception:
            pass

    github_svc = GitHubService(token=settings.github_token, repo=project.github_remote)
    ticket_svc = _ticket_svc(project_id)
    sync_map_svc = SyncMapService()

    agent = GithubSyncAgent(
        github_svc=github_svc,
        ticket_svc=ticket_svc,
        sync_map_svc=sync_map_svc,
        project_path=project_path,
        label_map=label_map,
    )

    sync_result = await agent.run(direction=body.direction)
    return GithubSyncResult(
        pulled=sync_result.pulled,
        pushed=sync_result.pushed,
        skipped=sync_result.skipped,
    )


@router.get("/{project_id}", response_model=Project)
async def get_project(project_id: str) -> Project:
    try:
        return await _loader().load_project(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
