"""Spend and run history of projects — ticket-689."""

from fastapi import Query

from tessera.config import settings
from tessera.models.usage import UsageBreakdown
from tessera.routers.projects.shared import new_router
from tessera.services.database import (
    PipelineRunSummary,
    ProjectUsage,
    get_project_usage,
    get_usage_breakdown,
    list_runs,
)

router = new_router()


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


@router.get("/usage/breakdown", response_model=UsageBreakdown)
async def get_usage_breakdown_global() -> UsageBreakdown:
    """La dépense de **tous** les projets, ventilée par projet, agent et modèle."""
    return UsageBreakdown.model_validate(await get_usage_breakdown(settings.ide_db_path, None))


@router.get("/{project_id}/usage/breakdown", response_model=UsageBreakdown)
async def get_usage_breakdown_for_project(project_id: str) -> UsageBreakdown:
    """La dépense de ce projet, ventilée par agent et par modèle."""
    return UsageBreakdown.model_validate(await get_usage_breakdown(settings.ide_db_path, project_id))
