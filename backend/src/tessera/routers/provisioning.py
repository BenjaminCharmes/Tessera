"""Put a project online: the one entry point — ADR-053, ticket-471.

``POST`` starts the plan in the background, ``GET`` reads what is missing
without writing anything. Progress is followed on ``WS /orchestrator/observe``
(``provisioning_step`` events), like a run (ADR-041). Nothing here deletes.
"""
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from tessera.config import settings
from tessera.models.project import Project
from tessera.routers.dependencies import require_valid_project_id
from tessera.services.politique_run import PolitiqueRun
from tessera.services.project_loader import load_project
from tessera.services.provisioning.launcher import (
    PROVISIONING_LOCK,
    ProvisioningSetup,
    SetupFactory,
    get_setup_factory,
    run_provisioning,
)
from tessera.services.provisioning.online_config import (
    OnlineConfig,
    OnlineConfigError,
    load_online_config,
)
from tessera.services.provisioning.plan import ProvisioningPlan
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

router = APIRouter(
    prefix="/projects",
    tags=["provisioning"],
    dependencies=[Depends(require_valid_project_id)],
)


class StepStateView(BaseModel):
    """What one step found; ``detail`` never holds a secret."""

    step: str
    state: str
    detail: str


class ProvisioningStarted(BaseModel):
    """The run is under way; its progress arrives on the observation socket."""

    project_id: str
    steps: list[str]


def _load(project_id: str) -> Project:
    try:
        return load_project(settings.ide_workspace_dir / project_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Project not found") from None


def _online_of(project: Project) -> OnlineConfig:
    try:
        online = load_online_config(Path(project.path))
    except OnlineConfigError as erreur:
        raise HTTPException(status_code=422, detail=str(erreur)) from None
    if online is None:
        raise HTTPException(
            status_code=422, detail="The project declares no 'online' block in agents.json"
        )
    return online


def _build(
    factory: SetupFactory, project: Project, online: OnlineConfig
) -> ProvisioningSetup:
    try:
        setup = factory(project.id, online, project.github_remote)
        # Vercel déploie la branche de base du projet, celle de sa politique de run.
        politique = PolitiqueRun.lire(Path(project.path))
        setup.context.base_branch = politique.base_branch or settings.github_base_branch
        return setup
    except Exception as erreur:
        # Ni message ni trace : la construction lit les jetons.
        _logger.error(
            "provisioning_setup_failed",
            extra={"project": project.id, "error": type(erreur).__name__},
        )
        raise HTTPException(status_code=500, detail="Provisioning could not start") from None


@router.post("/{project_id}/provision", response_model=ProvisioningStarted, status_code=202)
async def start_provisioning(
    project_id: str,
    background: BackgroundTasks,
    factory: SetupFactory = Depends(get_setup_factory),
) -> ProvisioningStarted:
    """Start the provisioning plan of the project, in the background."""
    project = _load(project_id)
    online = _online_of(project)
    if not PROVISIONING_LOCK.try_acquire(project_id):
        raise HTTPException(status_code=409, detail="A provisioning is already running")
    try:
        setup = _build(factory, project, online)
    except HTTPException:
        PROVISIONING_LOCK.release(project_id)
        raise
    background.add_task(run_provisioning, setup)
    return ProvisioningStarted(project_id=project_id, steps=[s.name for s in setup.steps])


@router.get("/{project_id}/provision", response_model=list[StepStateView])
async def read_provisioning(
    project_id: str,
    factory: SetupFactory = Depends(get_setup_factory),
) -> list[StepStateView]:
    """Read the state of every step: ``inspect`` only, no ``apply``, no event."""
    project = _load(project_id)
    setup = _build(factory, project, _online_of(project))
    sorties = await ProvisioningPlan(setup.steps).run(setup.context, dry_run=True)
    return [
        StepStateView(step=s.step, state=str(s.result.state), detail=s.result.detail)
        for s in sorties
    ]
