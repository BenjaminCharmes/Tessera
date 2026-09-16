import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

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
from vibe_ide.services.database import PipelineRunSummary, ProjectUsage, get_project_usage, list_runs
from vibe_ide.agents.github_sync import GithubSyncAgent
from vibe_ide.services.git_clone import CloneError, GitCloneService
from vibe_ide.services.github_service import GitHubService
from vibe_ide.services.planner import PlannerService
from vibe_ide.services.project_analyzer import ProjectAnalyzerService
from vibe_ide.services.project_importer import ImportError, ProjectImporter
from vibe_ide.services.project_creator import ProjectCreatorService
from vibe_ide.services.project_removal import (
    RemovalError,
    delete_project,
    describe_removal,
    detach_project,
)
from vibe_ide.services.vibe_artifacts import (
    ArtifactMode,
    apply_artifact_mode,
    default_mode_for,
    read_artifact_mode,
    tracked_artifact_paths,
)
from vibe_ide.services.git_link import (
    GitLinkError,
    RemoteNotEmpty,
    git_status,
    init_repository,
    link_remote,
)
from vibe_ide.services.project_loader import ProjectLoader, load_agents_config
from vibe_ide.services.providers import get_provider
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
    # Pure text-in/JSON-out: ProjectCreatorService writes files itself via
    # ProjectLoader, never through an SDK tool, and no cwd is threaded to it
    # here (ticket-044 merge-gate review, finding 2).
    provider = get_provider(
        settings.llm_provider, settings.anthropic_api_key,
        max_turns=settings.llm_max_turns, max_budget_usd=settings.llm_max_budget_usd,
        allow_tools=False,
    )
    svc = ProjectCreatorService(provider, settings.ide_prompts_dir, settings.ide_workspace_dir)
    agents_created = await svc._auto_create_missing_agents(
        roles=body.active_agents,
        project_name=project.name,
        project_description=project.description,
    )
    # Consigné explicitement : depuis que le défaut de lecture est `local`,
    # un projet créé qui ne déclare rien ne verserait plus ses ADR au dépôt.
    await apply_artifact_mode(
        settings.ide_workspace_dir / project.id, default_mode_for("create")
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
    # Un dépôt importé existait avant vibe-ide : ses artefacts restent locaux
    # tant que l'utilisateur n'a pas choisi de les partager (ADR-021).
    await apply_artifact_mode(
        settings.ide_workspace_dir / project.id, default_mode_for("import")
    )
    return ProjectImportResponse(project=project)


@router.post("/clone", response_model=CloneProjectResponse, status_code=201)
async def clone_project(body: CloneProjectRequest) -> CloneProjectResponse:
    # Pure text-in/JSON-out: no filesystem tools needed (ticket-044 review, finding 4).
    provider = get_provider(
        settings.llm_provider, settings.anthropic_api_key,
        max_turns=settings.llm_max_turns, max_budget_usd=settings.llm_max_budget_usd,
        allow_tools=False,
    )
    analyzer = ProjectAnalyzerService(provider, settings.ide_prompts_dir)
    svc = GitCloneService(settings.ide_workspace_dir, analyzer)
    try:
        return await svc.clone(
            repo_url=body.repo_url,
            project_id=body.project_id,
        )
    except CloneError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# Note : les routes avec sous-chemin spécifique doivent être avant /{project_id}
@router.get("/{project_id}/usage", response_model=ProjectUsage)
async def get_usage(project_id: str) -> ProjectUsage:
    data = await get_project_usage(settings.ide_db_path, project_id)
    return ProjectUsage(**data)


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
    # Pure text-in/JSON-out: no filesystem tools needed (ticket-044 review, finding 4).
    provider = get_provider(
        settings.llm_provider, settings.anthropic_api_key,
        max_turns=settings.llm_max_turns, max_budget_usd=settings.llm_max_budget_usd,
        allow_tools=False,
    )
    svc = PlannerService(provider, settings.ide_prompts_dir, settings.ide_workspace_dir)
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
    provider = get_provider(
        settings.llm_provider, settings.anthropic_api_key,
        max_turns=settings.llm_max_turns, max_budget_usd=settings.llm_max_budget_usd,
        allow_tools=False,
    )
    svc = ProjectAnalyzerService(provider, settings.ide_prompts_dir)
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


# ------------------------------------------------------------------
# Liaison git — ticket-061
# ------------------------------------------------------------------


class GitStatusResponse(BaseModel):
    is_repository: bool
    has_commits: bool
    remote_url: str | None = None
    # Renseigné quand le projet vit dans un dépôt qui n'est pas le sien :
    # `init` créera alors bien son propre dépôt (ticket-061).
    nested_in: str | None = None


class LinkRemoteRequest(BaseModel):
    repo_url: str
    # L'utilisateur confirme les deux cas qu'il est seul à pouvoir trancher :
    # un dépôt distant non vide, et un `origin` déjà configuré.
    confirmed: bool = False


def _require_project_path(project_id: str) -> Path:
    project_path = settings.ide_workspace_dir / project_id
    if not project_path.is_dir():
        raise HTTPException(status_code=404, detail=f"Projet introuvable : {project_id}")
    return project_path


def _repo_slug(repo_url: str) -> str | None:
    """Extrait `owner/repo` d'une URL GitHub, pour interroger l'API."""
    match = re.search(r"github\.com[:/]([\w.\-]+/[\w.\-]+?)(?:\.git)?/?$", repo_url.strip())
    return match.group(1) if match else None


@router.get("/{project_id}/git/status", response_model=GitStatusResponse)
async def get_git_status(project_id: str) -> GitStatusResponse:
    status = await git_status(_require_project_path(project_id))
    return GitStatusResponse(
        is_repository=status.is_own_repository,
        has_commits=status.has_commits,
        remote_url=status.remote_url,
        nested_in=status.is_nested_in,
    )


@router.post("/{project_id}/git/init", response_model=GitStatusResponse)
async def init_git(project_id: str) -> GitStatusResponse:
    """Initialise un dépôt dans le projet. Sans effet s'il en a déjà un."""
    try:
        status = await init_repository(_require_project_path(project_id))
    except GitLinkError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return GitStatusResponse(
        is_repository=status.is_own_repository,
        has_commits=status.has_commits,
        remote_url=status.remote_url,
        nested_in=status.is_nested_in,
    )


@router.post("/{project_id}/git/link", response_model=GitStatusResponse)
async def link_git_remote(project_id: str, body: LinkRemoteRequest) -> GitStatusResponse:
    """Attache un remote GitHub au projet, après vérification du dépôt distant."""
    project_path = _require_project_path(project_id)

    # Le dépôt distant n'est interrogé que si un token le permet. Sans token,
    # on ne peut rien affirmer : on exige alors une confirmation explicite
    # plutôt que de supposer le dépôt vide.
    remote_is_empty = body.confirmed
    slug = _repo_slug(body.repo_url)
    if settings.github_token and slug:
        info = await GitHubService(token=settings.github_token, repo=slug).get_repository_info()
        if not info.exists:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Le dépôt '{slug}' est introuvable, ou le GITHUB_TOKEN "
                    "configuré n'y a pas accès."
                ),
            )
        remote_is_empty = info.is_empty

    try:
        status = await link_remote(
            project_path,
            body.repo_url,
            remote_is_empty=remote_is_empty,
            confirmed=body.confirmed,
        )
    except RemoteNotEmpty as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except GitLinkError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return GitStatusResponse(
        is_repository=status.is_own_repository,
        has_commits=status.has_commits,
        remote_url=status.remote_url,
        nested_in=status.is_nested_in,
    )


# ------------------------------------------------------------------
# Artefacts vibe-ide — ticket-062
# ------------------------------------------------------------------


class ArtifactModeResponse(BaseModel):
    mode: ArtifactMode
    #: Artefacts déjà dans l'index git. Passer en `local` ne les en sort pas :
    #: git continue de suivre ce qu'il suit déjà.
    already_tracked: list[str] = []


class SetArtifactModeRequest(BaseModel):
    mode: ArtifactMode


@router.get("/{project_id}/artifacts", response_model=ArtifactModeResponse)
async def get_artifact_mode(project_id: str) -> ArtifactModeResponse:
    project_path = _require_project_path(project_id)
    return ArtifactModeResponse(
        mode=read_artifact_mode(project_path),
        already_tracked=await tracked_artifact_paths(project_path),
    )


@router.put("/{project_id}/artifacts", response_model=ArtifactModeResponse)
async def set_artifact_mode(
    project_id: str, body: SetArtifactModeRequest
) -> ArtifactModeResponse:
    """Choisit si les artefacts vibe-ide partent dans le dépôt du projet.

    L'exclusion passe par `.git/info/exclude`, jamais par `.gitignore` : ce
    dernier est versionné, donc le modifier annoncerait dans un diff ce qu'on
    voulait justement garder hors du dépôt.

    Les fichiers **déjà suivis** sont signalés, pas retirés : les sortir de
    l'index est un `git rm --cached`, qui se décide.
    """
    project_path = _require_project_path(project_id)
    await apply_artifact_mode(project_path, body.mode)
    return ArtifactModeResponse(
        mode=body.mode,
        already_tracked=await tracked_artifact_paths(project_path),
    )


# ------------------------------------------------------------------
# Retrait d'un projet — ticket-063
# ------------------------------------------------------------------


class RemovalPlanResponse(BaseModel):
    project_id: str
    #: Le chemin réellement visé, liens résolus : c'est lui qu'il faut montrer
    #: avant de décider.
    real_path: str
    is_symlink: bool
    unpushed_commits: int


class DetachResponse(BaseModel):
    detached: bool
    #: Où les fichiers ont été déplacés, ou le lien retiré.
    moved_to: str


@router.get("/{project_id}/removal-plan", response_model=RemovalPlanResponse)
async def get_removal_plan(project_id: str) -> RemovalPlanResponse:
    """Décrit ce qu'un retrait toucherait, sans rien modifier."""
    plan = await describe_removal(_require_project_path(project_id))
    return RemovalPlanResponse(
        project_id=plan.project_id,
        real_path=plan.real_path,
        is_symlink=plan.is_symlink,
        unpushed_commits=plan.unpushed_commits,
    )


@router.post("/{project_id}/detach", response_model=DetachResponse)
async def detach(project_id: str) -> DetachResponse:
    """Retire le projet de l'IDE. Les fichiers restent."""
    try:
        moved_to = await detach_project(_require_project_path(project_id))
    except RemovalError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return DetachResponse(detached=True, moved_to=moved_to)


@router.delete("/{project_id}", status_code=204)
async def delete(project_id: str, confirmed: bool = Query(default=False)) -> None:
    """Efface définitivement un projet. Ne franchit jamais un lien symbolique."""
    project_path = _require_project_path(project_id)
    try:
        await delete_project(
            project_path, confirmed=confirmed, workspace=settings.ide_workspace_dir
        )
    except RemovalError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
