"""Events endpoint for finished runs — ticket-280.

A finished run's events are already in ``agent_events``; nothing here runs
agents. The endpoint exposes them so the frontend can replay a run without
relaunching it (ticket-281).
"""
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from tessera.config import settings
from tessera.services.database import get_run_events
from tessera.services.run_registry import RUN_REGISTRY
from tessera.services.run_status import (
    RunStatus,
    statut_d_un_run_vivant,
    statut_en_base,
)

router = APIRouter(prefix="/runs", tags=["runs"])


class RunEvent(BaseModel):
    """One persisted pipeline event, in the same shape as the WebSocket wire."""

    type: str
    agent: str | None = None
    data: dict[str, Any]
    timestamp: str


@router.get("/{run_id}", response_model=RunStatus)
async def get_status(run_id: str) -> RunStatus:
    """Where a run stands, by the id ``POST /orchestrator/run`` handed back.

    A live run is read from the registry (current ticket, tickets done and
    left). A finished one is read from ``pipeline_runs``: ``faits`` are the
    tickets the queue played (a ticket skipped because already done leaves no
    row), ``restants`` those the last ``queue_progress`` still announced.
    ``statut`` is ``en cours``, ``terminé`` or ``interrompu``.

    Returns 404 when the id is unknown, which includes a run that could not be
    persisted and has since closed.
    """
    vivant = RUN_REGISTRY.get(run_id)
    if vivant is not None:
        return statut_d_un_run_vivant(vivant)
    statut = await statut_en_base(settings.ide_db_path, run_id)
    if statut is None:
        raise HTTPException(status_code=404, detail=f"Run inconnu : {run_id}")
    return statut


@router.get("/{run_id}/events", response_model=list[RunEvent])
async def get_events(run_id: str) -> list[RunEvent]:
    """Return the persisted events of a finished run, in emission order.

    ``agent_token`` chunks are excluded: the replay view needs the final text
    only, already in ``agent_done``.

    Returns 404 when the run_id is unknown. For a per-ticket row inside a
    queue, returns only events that belong to that ticket (filtered by
    ``ticket_id`` in SQL, against the parent run's events).

    Authentication is not checked here: ``StaticTokenMiddleware``
    (``tessera/auth.py``, installed in ``main.py``) guards every path but
    ``/health``, this one included.
    """
    events = await get_run_events(settings.ide_db_path, run_id)
    if events is None:
        raise HTTPException(status_code=404, detail=f"Run inconnu : {run_id}")
    return [RunEvent(**e) for e in events]
