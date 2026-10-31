"""Creating a project: new, import, clone, from template — ticket-689."""

from fastapi import HTTPException

from tessera.config import settings
from tessera.models.project import (
    CloneProjectRequest,
    CloneProjectResponse,
    ProjectCreate,
    ProjectCreationResult,
    ProjectFromTemplateRequest,
    ProjectFromTemplateResult,
    ProjectImport,
    ProjectImportResponse,
)
from tessera.routers.projects.shared import loader, new_router
from tessera.services.artifacts import apply_artifact_mode, default_mode_for
from tessera.services.git_clone import CloneError, GitCloneService
from tessera.services.git_link import init_repository
from tessera.services.project_analyzer import ProjectAnalyzerService
from tessera.services.project_creator import ProjectCreatorService
from tessera.services.project_from_template import create_project_from_template as _create_from_template
from tessera.services.project_importer import ImportError, ProjectImporter
from tessera.services.providers.par_role import provider_pour_role
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

router = new_router()


@router.post("", response_model=ProjectCreationResult, status_code=201)
async def create_project(body: ProjectCreate) -> ProjectCreationResult:
    try:
        project = await loader().create_project(body)
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


@router.post("/from-template", response_model=ProjectFromTemplateResult, status_code=201)
async def create_project_from_template(
    body: ProjectFromTemplateRequest,
) -> ProjectFromTemplateResult:
    """Crée un projet depuis le gabarit fastapi-react en un appel.

    Attribue automatiquement des ports libres, crée la structure de dossiers,
    copie le gabarit avec substitution des marqueurs, et initialise le dépôt git.
    Aucun dépôt GitHub n'est créé.
    """
    try:
        return await _create_from_template(
            workspace=settings.ide_workspace_dir,
            project_id=body.project_id,
            name=body.name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
