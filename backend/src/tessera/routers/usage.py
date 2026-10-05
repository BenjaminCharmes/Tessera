"""Usage statistics — ticket-201.

Sous `/usage` et non `/projects` : la vue d'ensemble n'a pas de projet, et
`/projects/{project_id}` aurait capturé un segment `stats`.
"""
from fastapi import APIRouter, HTTPException, Query

from tessera.config import settings
from tessera.models.usage import RecentRun, UsageStats
from tessera.services.usage_stats import PERIODS, recent_runs, usage_stats

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("/stats", response_model=UsageStats)
async def get_usage_stats(
    days: int = Query(30),
    project_id: str | None = Query(None),
) -> UsageStats:
    """Totals, daily series, breakdowns and run quality over the last `days` UTC days."""
    if days not in PERIODS:
        # Une période libre ferait grossir la série sans borne ; l'écran n'en
        # propose que trois.
        raise HTTPException(status_code=422, detail=f"days must be one of {PERIODS}")
    return await usage_stats(settings.ide_db_path, days, project_id)


@router.get("/recent-runs", response_model=list[RecentRun])
async def get_recent_runs(
    days: int = Query(30),
    project_id: str | None = Query(None),
    # Borné : la carte avance par vingt, et une liste de mille lignes ne se lit pas.
    limit: int = Query(10, ge=1, le=200),
    q: str | None = Query(None, max_length=100),
) -> list[RecentRun]:
    """Latest ticket runs of the period, searchable by ticket or project — ticket-335."""
    if days not in PERIODS:
        raise HTTPException(status_code=422, detail=f"days must be one of {PERIODS}")
    recherche = q.strip() if q else None
    return await recent_runs(
        settings.ide_db_path, days, project_id, limit=limit, recherche=recherche or None
    )
