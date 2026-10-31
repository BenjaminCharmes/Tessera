"""Branch cleanup of a project — ticket-070, ticket-689."""

from pydantic import BaseModel

from tessera.config import settings
from tessera.routers.projects.shared import new_router
from tessera.services.branch_cleanup import PlanDeNettoyage, plan_de_nettoyage, supprimer_branches

router = new_router()


class CleanupRequest(BaseModel):
    """Les branches que l'utilisateur a choisi de supprimer, parmi le plan."""

    branches: list[str]


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
