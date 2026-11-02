"""Reading projects: list, overview, icon, context, one project — ticket-689."""

import asyncio

from fastapi import HTTPException
from fastapi.responses import FileResponse

from tessera.models.project import Project, ProjectContext
from tessera.models.ticket import TicketStatus
from tessera.routers.projects.shared import loader, new_router, require_project_path, ticket_svc
from tessera.config import settings
from tessera.services.adr import lire_contraintes
from tessera.services.process_registry import PROCESS_REGISTRY
from tessera.services.project_loader import (
    fait_tourner_l_ide,
    load_agents_config,
    load_services_config,
)
from tessera.services.project_overview import ProjectOverview, build_overview, find_icon
from tessera.services.run_registry import RUN_REGISTRY

router = new_router()

_OPEN_STATUSES = {TicketStatus.todo, TicketStatus.in_progress, TicketStatus.in_review, TicketStatus.blocked}


@router.get("", response_model=list[Project])
async def list_projects() -> list[Project]:
    return await loader().list_projects()


# `/overview` doit rester avant toute route `/{project_id}` : sinon « overview »
# serait lu comme un identifiant de projet (ticket-398). Ce routeur est inclus
# le premier, et `get_project` vient après `/overview` dans ce fichier.
@router.get("/overview", response_model=list[ProjectOverview])
async def get_projects_overview() -> list[ProjectOverview]:
    """Tout ce qu'affiche une carte de projet, en une seule requête."""
    projets = await loader().list_projects()
    return list(
        await asyncio.gather(
            *(
                build_overview(
                    p,
                    run_actif=RUN_REGISTRY.projet_occupe(p.id),
                    # Le projet qui fait tourner l'IDE n'a rien à lancer depuis
                    # l'IDE : ce serait un second backend sur un port pris.
                    services_declares=bool(load_services_config(p.path))
                    and not fait_tourner_l_ide(p.path),
                    services_en_cours=any(
                        s.en_cours for s in PROCESS_REGISTRY.services_de(p.id)
                    ),
                )
                for p in projets
            )
        )
    )


@router.get("/{project_id}/icon")
async def get_project_icon(project_id: str) -> FileResponse:
    """L'icône d'app du projet, parmi des chemins fixes ; 404 sans icône."""
    trouvee = find_icon(require_project_path(project_id))
    if trouvee is None:
        raise HTTPException(status_code=404, detail="Ce projet n'a pas d'icône.")
    chemin, media_type = trouvee
    return FileResponse(chemin, media_type=media_type)


@router.get("/{project_id}/context", response_model=ProjectContext)
async def get_project_context(project_id: str) -> ProjectContext:
    try:
        project = await loader().load_project(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    project_path = settings.ide_workspace_dir / project_id
    all_tickets = await ticket_svc(project_id).list_tickets()
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


@router.get("/{project_id}", response_model=Project)
async def get_project(project_id: str) -> Project:
    try:
        return await loader().load_project(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
