"""The parent run of an interrupted queue says so — ticket-456.

The envelope row was closed from the last ticket's result alone: a queue that
stopped on "ticket-001 non mergé" ended on an approved ticket, so the API
reported `approved=True`, `final_status=done`, `arret=None`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import aiosqlite
import pytest

from tessera.config import settings
from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services.database import init_db
from tessera.services.event_hub import EventHub
from tessera.services.livraison import Livraison
from tessera.services.pipeline_events import PipelineResult
from tessera.services.run_executor import executer
from tessera.services.run_registry import RunRegistry

from .test_orchestrator_livraison import (
    _construire,
    _construire_avec_surveiller,
    _resultat,
)


class _CIWatcherQuiEchoue:
    async def attendre_merge(self, project_id: str, ticket_id: str, **_: Any) -> bool:
        return False


def _ticket(ticket_id: str, depends_on: list[str]) -> Ticket:
    return Ticket(
        id=ticket_id, title="titre", type=TicketType.feat,
        status=TicketStatus.todo, priority=TicketPriority.medium,
        agent="codeur", body="corps", depends_on=depends_on,
    )


async def _lancer_la_file(
    orch: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, ids: list[str]
) -> dict[str, Any]:
    """Run the queue through `executer` and return the envelope row."""
    db_path = tmp_path / "tessera.db"
    await init_db(db_path)
    monkeypatch.setattr(settings, "ide_workspace_dir", tmp_path / "workspace")
    monkeypatch.setattr(settings, "ide_db_path", db_path)

    registry = RunRegistry()
    run = registry.ouvrir("proj", mode="queue")
    await executer(run, orch, EventHub(), registry, ticket_ids=ids)

    async with aiosqlite.connect(str(db_path)) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT approved, final_status, arret FROM pipeline_runs WHERE id=?",
            (run.run_id,),
        ) as cursor:
            row = await cursor.fetchone()
    assert row is not None
    return dict(row)


async def test_unmerged_ticket_leaves_the_parent_run_unapproved_with_its_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tickets = AsyncMock()
    tickets.get_ticket.side_effect = lambda tid: {
        "ticket-001": _ticket("ticket-001", []),
        "ticket-002": _ticket("ticket-002", ["ticket-001"]),
    }.get(tid)

    async def _livrer(result: PipelineResult) -> Livraison:
        return Livraison(pr_number=7, arret=None)

    orch = _construire_avec_surveiller(
        tmp_path,
        [_resultat("ticket-001"), _resultat("ticket-002")],
        _livrer,
        ci_watcher=_CIWatcherQuiEchoue(),
        ticket_service=tickets,
    )

    parent = await _lancer_la_file(orch, tmp_path, monkeypatch, ["ticket-001", "ticket-002"])

    assert parent["approved"] == 0
    assert "interrompue" in (parent["arret"] or "")
    assert "ticket-001 non mergé" in parent["arret"]


async def test_interrupted_queue_parent_run_status_is_not_done(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tickets = AsyncMock()
    tickets.get_ticket.side_effect = lambda tid: {
        "ticket-001": _ticket("ticket-001", []),
        "ticket-002": _ticket("ticket-002", ["ticket-001"]),
    }.get(tid)

    async def _livrer(result: PipelineResult) -> Livraison:
        return Livraison(pr_number=7, arret=None)

    orch = _construire_avec_surveiller(
        tmp_path,
        [_resultat("ticket-001"), _resultat("ticket-002")],
        _livrer,
        ci_watcher=_CIWatcherQuiEchoue(),
        ticket_service=tickets,
    )

    parent = await _lancer_la_file(orch, tmp_path, monkeypatch, ["ticket-001", "ticket-002"])

    assert parent["final_status"] != TicketStatus.done.value


async def test_completed_queue_keeps_the_parent_run_approved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _livrer(result: PipelineResult) -> Livraison:
        return Livraison(pr_number=7, merged=True)

    orch = _construire(
        tmp_path, [_resultat("ticket-001"), _resultat("ticket-002")], _livrer
    )

    parent = await _lancer_la_file(orch, tmp_path, monkeypatch, ["ticket-001", "ticket-002"])

    assert parent["approved"] == 1
    assert parent["final_status"] == TicketStatus.done.value
    assert parent["arret"] is None


async def test_orchestrator_forgets_the_interruption_of_a_previous_queue(
    tmp_path: Path,
) -> None:
    async def _livrer(result: PipelineResult) -> Livraison:
        return Livraison(pr_number=7, merged=True)

    orch = _construire(tmp_path, [_resultat("ticket-001", approuve=False)], _livrer)
    await orch.run_queue("proj", ["ticket-001"])
    assert orch.interruption is not None
    assert "non approuvé" in orch.interruption

    orch._resultats.append(_resultat("ticket-002"))
    await orch.run_queue("proj", ["ticket-002"])
    assert orch.interruption is None
