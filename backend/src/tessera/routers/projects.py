import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from tessera.config import settings
from tessera.models.project import (
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
from tessera.models.ticket import TicketStatus
from tessera.services.database import get_usage_breakdown, PipelineRunSummary, ProjectUsage, get_project_usage, list_runs
from tessera.agents.github_sync import GithubSyncAgent
from tessera.services.adr import lire_contraintes
from tessera.services.git_clone import CloneError, GitCloneService
from tessera.services.github_service import GitHubService
from tessera.services.planner import PlannerService
from tessera.services.project_analyzer import ProjectAnalyzerService
from tessera.services.project_importer import ImportError, ProjectImporter
from tessera.services.project_creator import ProjectCreatorService
from tessera.services.project_removal import (
    RemovalError,
    delete_project,
    describe_removal,
    detach_project,
)
from tessera.services.branch_cleanup import PlanDeNettoyage, plan_de_nettoyage, supprimer_branches
from tessera.services.artifacts import (
    ArtifactMode,
    apply_artifact_mode,
    default_mode_for,
    read_artifact_mode,
    tracked_artifact_paths,
)
from tessera.services.git_link import (
    GitLinkError,
    RemoteNotEmpty,
    git_status,
    init_repository,
    link_remote,
)
from tessera.services.cost_calculator import modeles_connus
from tessera.services.politique_run import PolitiqueRun
from tessera.services.run_registry import RUN_REGISTRY
from tessera.models.agent import FallbackConfig
from tessera.routers.dependencies import require_valid_project_id
from tessera.services.project_loader import (
    AgentAbsentDuProjet,
    ModeleInconnu,
    ProjectLoader,
    load_agents_config,
    load_pipeline_config,
    set_agent_model,
    set_agent_provider,
    set_pipeline_settings,
)
from tessera.services.providers.noms import PROVIDERS_ANTHROPIC, PROVIDERS_CONNUS, ProviderInconnu
from tessera.services.providers.par_role import modele_du_role, provider_pour_role
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)
from tessera.services.sync_map import SyncMapService
from tessera.services.ticket_service import TicketService

router = APIRouter(
    prefix="/projects",
    tags=["projects"],
    dependencies=[Depends(require_valid_project_id)],
)

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
    provider = provider_pour_role(None, "project-creator", allow_tools=False)
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
    # Le dépôt vient **après** le mode des artefacts, jamais avant : le commit
    # initial d'`init_repository` stage avec `git add -A`, donc ce qui n'est
    # pas encore exclu y entre — et, sur un dépôt client, part au premier push
    # (ADR-021, ADR-023).
    #
    # Sans dépôt à sa racine, un projet est inutilisable par le pipeline :
    # `GitWorkspaceService` lève `NotAGitRepository` et le run s'arrête avant
    # la première branche (ADR-024). Mais un git indisponible ne doit pas faire
    # échouer la création — le projet existe déjà sur disque, et lever ici
    # laisserait l'utilisateur avec un projet créé et un message d'échec.
    repository_ready = False
    try:
        await init_repository(settings.ide_workspace_dir / project.id)
        repository_ready = True
    except Exception as exc:  # noqa: BLE001 — l'état part dans la réponse
        _logger.warning(
            "project_git_init_failed",
            extra={"project_id": project.id, "error": str(exc)},
        )
    return ProjectCreationResult(
        project=project,
        agents_created=agents_created,
        repository_ready=repository_ready,
    )


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
    # Un dépôt importé existait avant Tessera : ses artefacts restent locaux
    # tant que l'utilisateur n'a pas choisi de les partager (ADR-021).
    await apply_artifact_mode(
        settings.ide_workspace_dir / project.id, default_mode_for("import")
    )
    return ProjectImportResponse(project=project)


@router.post("/clone", response_model=CloneProjectResponse, status_code=201)
async def clone_project(body: CloneProjectRequest) -> CloneProjectResponse:
    # Pure text-in/JSON-out: no filesystem tools needed (ticket-044 review, finding 4).
    provider = provider_pour_role(None, "project-analyzer", allow_tools=False)
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

    recent_decisions = lire_contraintes(project_path / "memory")

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
    # Le projet déclare `git_root: ancestor` : travailler dans le dépôt qui le
    # contient est son mode normal (ADR-028), pas une anomalie à corriger.
    # Sans ce champ, l'écran annonçait « ce projet n'est pas versionné » et
    # proposait d'imbriquer un dépôt dans celui de Tessera (ticket-171).
    uses_parent_repository: bool = False


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
    chemin = _require_project_path(project_id)
    status = await git_status(chemin)
    return GitStatusResponse(
        is_repository=status.is_own_repository,
        has_commits=status.has_commits,
        remote_url=status.remote_url,
        nested_in=status.is_nested_in,
        uses_parent_repository=PolitiqueRun.lire(chemin).dans_le_depot_parent,
    )


@router.post("/{project_id}/git/init", response_model=GitStatusResponse)
async def init_git(project_id: str) -> GitStatusResponse:
    """Initialise un dépôt dans le projet. Sans effet s'il en a déjà un.

    Refusé sur un projet en `git_root: ancestor` : il travaille dans le dépôt
    qui le contient (ADR-028), et l'initialiser en imbriquerait un second —
    ce qu'ADR-024 existe pour empêcher. Le refus est ici et pas seulement à
    l'écran : une garde qui dépend de l'interface n'en est pas une (ADR-027).
    """
    chemin = _require_project_path(project_id)
    if PolitiqueRun.lire(chemin).dans_le_depot_parent:
        raise HTTPException(
            status_code=422,
            detail=(
                "Ce projet déclare `git_root: ancestor` : il travaille dans le "
                "dépôt qui le contient. Initialiser un dépôt ici en imbriquerait "
                "un second. Retire `git_root` de son agents.json pour lui en "
                "donner un propre."
            ),
        )
    try:
        status = await init_repository(chemin)
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
# Artefacts Tessera — ticket-062
# ------------------------------------------------------------------


class ArtifactModeResponse(BaseModel):
    mode: ArtifactMode
    #: Artefacts déjà dans l'index git. Passer en `local` ne les en sort pas :
    #: git continue de suivre ce qu'il suit déjà.
    already_tracked: list[str] = []


class SetArtifactModeRequest(BaseModel):
    mode: ArtifactMode


class CleanupRequest(BaseModel):
    """Les branches que l'utilisateur a choisi de supprimer, parmi le plan."""

    branches: list[str]


class ProjectAgentConfig(BaseModel):
    role: str
    model: str
    max_tokens: int
    active: bool = True
    provider: str = "agent_sdk"
    fallback: FallbackConfig | None = None


class ProjectAgentsResponse(BaseModel):
    agents: list[ProjectAgentConfig]
    #: Les seuls modèles proposables sur un provider Anthropic : ceux dont
    #: l'app sait calculer le coût.
    known_models: list[str]
    #: Les providers qu'un rôle peut déclarer (ticket-188).
    known_providers: list[str]
    #: Par provider, la liste proposable — vide quand le nom est libre.
    known_models_by_provider: dict[str, list[str]]


class SetModelRequest(BaseModel):
    model: str
    provider: str | None = None
    fallback: FallbackConfig | None = None


def _modeles_par_provider() -> dict[str, list[str]]:
    return {
        nom: modeles_connus() if nom in PROVIDERS_ANTHROPIC else []
        for nom in PROVIDERS_CONNUS
    }


@router.get("/{project_id}/agents", response_model=ProjectAgentsResponse)
async def get_project_agents(project_id: str) -> ProjectAgentsResponse:
    """Les agents déclarés par ce projet, et le modèle que chacun utilise."""
    try:
        configs = load_agents_config(settings.ide_workspace_dir / project_id)
    except ProviderInconnu as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ProjectAgentsResponse(
        agents=[
            ProjectAgentConfig(
                role=c.role, model=c.model, max_tokens=c.max_tokens, active=c.active,
                provider=c.provider, fallback=c.fallback,
            )
            for c in configs
        ],
        known_models=modeles_connus(),
        known_providers=list(PROVIDERS_CONNUS),
        known_models_by_provider=_modeles_par_provider(),
    )


@router.put("/{project_id}/agents/{role}", response_model=ProjectAgentsResponse)
async def set_project_agent_model(
    project_id: str, role: str, body: SetModelRequest
) -> ProjectAgentsResponse:
    """Change le modèle d'un agent pour **ce projet** (ticket-080), et depuis
    ticket-188 son provider et son repli. `fallback` omis : le repli ne bouge
    pas ; `fallback: null` : il est retiré."""
    project_path = settings.ide_workspace_dir / project_id
    try:
        if body.provider is not None or "fallback" in body.model_fields_set:
            actuel = next(
                (c for c in load_agents_config(project_path) if c.role == role), None
            )
            if actuel is None:
                raise AgentAbsentDuProjet(f"L'agent '{role}' n'est pas déclaré ici")
            repli = (
                body.fallback.model_dump() if body.fallback is not None else None
            ) if "fallback" in body.model_fields_set else (
                actuel.fallback.model_dump() if actuel.fallback is not None else None
            )
            set_agent_provider(project_path, role, body.provider or actuel.provider, repli)
        set_agent_model(project_path, role, body.model)
    except (ModeleInconnu, ProviderInconnu) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AgentAbsentDuProjet as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return await get_project_agents(project_id)


class PipelineReglages(BaseModel):
    """La configuration effective du pipeline d'un projet (ticket-196)."""

    max_review_rounds: int
    testeur_enabled: bool
    test_command: str | None
    securite_enabled: bool
    validateur_enabled: bool
    autonomy: str
    merge_without_ci: bool


class PipelineReglagesPatch(BaseModel):
    """Les seuls champs à changer ; les autres ne bougent pas."""

    max_review_rounds: int | None = None
    testeur_enabled: bool | None = None
    test_command: str | None = None
    securite_enabled: bool | None = None
    validateur_enabled: bool | None = None
    autonomy: str | None = None
    merge_without_ci: bool | None = None


_NIVEAUX = ("commit", "pr", "merge")


def _reglages(project_path: Path) -> PipelineReglages:
    cfg = load_pipeline_config(project_path)
    politique = PolitiqueRun.lire(project_path)
    return PipelineReglages(
        max_review_rounds=cfg.max_review_rounds,
        testeur_enabled=cfg.testeur_enabled,
        test_command=cfg.test_command,
        securite_enabled=cfg.securite_enabled,
        validateur_enabled=cfg.validateur_enabled,
        autonomy=politique.autonomy.value,
        merge_without_ci=politique.merge_without_ci,
    )


@router.get("/{project_id}/pipeline", response_model=PipelineReglages)
async def get_pipeline_settings(project_id: str) -> PipelineReglages:
    """Ce que le pipeline de ce projet fait, défauts appliqués."""
    return _reglages(_require_project_path(project_id))


@router.patch("/{project_id}/pipeline", response_model=PipelineReglages)
async def set_pipeline_settings_route(
    project_id: str, body: PipelineReglagesPatch
) -> PipelineReglages:
    """Change les réglages reçus, en préservant le reste du manifeste.

    Refusé pendant un run : la politique est lue une fois avant le premier
    agent (ADR-027), un changement ne vaudrait qu'au run suivant, et l'écran
    doit le dire plutôt que laisser croire à un effet immédiat.
    """
    project_path = _require_project_path(project_id)
    if RUN_REGISTRY.projet_occupe(project_id):
        raise HTTPException(
            status_code=409,
            detail="Un run est en cours : les réglages s'appliqueront au run suivant, "
            "modifie-les une fois le run terminé.",
        )
    recus = body.model_dump(exclude_unset=True)
    actuel = _reglages(project_path)
    fusion = actuel.model_copy(update=recus)
    if fusion.autonomy not in _NIVEAUX:
        raise HTTPException(
            status_code=400,
            detail=f"autonomy inconnue : {fusion.autonomy!r}. Valeurs : {', '.join(_NIVEAUX)}.",
        )
    if fusion.testeur_enabled and not (fusion.test_command or "").strip():
        # Un flag à vrai sans commande valide est pire qu'un flag à faux : le
        # lanceur avale l'erreur et rend `True`, si bien que l'absence de
        # tests se lirait comme des tests verts.
        raise HTTPException(
            status_code=400,
            detail="testeur_enabled exige une test_command : sans elle, l'absence "
            "de tests se lirait comme des tests verts.",
        )
    pipeline = {k: v for k, v in recus.items() if k not in ("autonomy", "merge_without_ci")}
    racine = {k: v for k, v in recus.items() if k in ("autonomy", "merge_without_ci")}
    try:
        set_pipeline_settings(project_path, pipeline=pipeline, racine=racine)
    except AgentAbsentDuProjet as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _reglages(project_path)


@router.get("/usage/breakdown")
async def get_usage_breakdown_global() -> dict[str, object]:
    """La dépense de **tous** les projets, ventilée par projet, agent et modèle."""
    return await get_usage_breakdown(settings.ide_db_path, None)


@router.get("/{project_id}/usage/breakdown")
async def get_usage_breakdown_for_project(project_id: str) -> dict[str, object]:
    """La dépense de ce projet, ventilée par agent et par modèle."""
    return await get_usage_breakdown(settings.ide_db_path, project_id)


@router.get("/{project_id}/branches/cleanup", response_model=PlanDeNettoyage)
async def get_cleanup_plan(project_id: str) -> PlanDeNettoyage:
    """Ce qui peut être supprimé sans rien perdre — à lire avant d'agir."""
    return await plan_de_nettoyage(settings.ide_workspace_dir / project_id)


@router.post("/{project_id}/branches/cleanup", response_model=list[str])
async def run_cleanup(project_id: str, body: CleanupRequest) -> list[str]:
    """Supprime les branches demandées qui figurent encore au plan.

    Le plan est recalculé côté serveur : entre l'affichage et le clic, un run a
    pu committer sur l'une de ces branches (ticket-070).
    """
    return await supprimer_branches(
        settings.ide_workspace_dir / project_id, body.branches
    )


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
    """Choisit si les artefacts Tessera partent dans le dépôt du projet.

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
