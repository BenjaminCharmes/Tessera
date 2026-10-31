"""Project routes, one module per resource — ticket-689.

`listing` vient en premier : `/projects/overview` doit être enregistré avant
`/projects/{project_id}`, sinon « overview » serait lu comme un identifiant de
projet (ticket-398). Les autres routeurs ne portent aucune route à un seul
segment variable, leur ordre est libre.
"""

from fastapi import APIRouter

from tessera.routers.projects import (
    actions,
    agents,
    artifacts,
    cleanup,
    creation,
    git,
    listing,
    pipeline,
    removal,
    usage,
)

router = APIRouter()

for _sub in (
    listing,
    creation,
    usage,
    actions,
    git,
    artifacts,
    agents,
    pipeline,
    cleanup,
    removal,
):
    router.include_router(_sub.router)
