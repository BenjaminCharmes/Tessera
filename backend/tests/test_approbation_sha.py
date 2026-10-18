"""Le SHA d'approbation et sa trace — ticket-492.

Couverture :
- `sha_approbation` : `approved_sha` et `pushed_sha` s'écrivent sur la ligne du
  run ; `sha_pousse_du_ticket` rend le plus récent, ou `None` ;
- `suivre_documentation` : le SHA suit le commit de documentation du pipeline,
  seulement si la tête valait encore le SHA approuvé juste avant ;
- l'orchestrateur bloque le ticket (événement + statut du résultat) quand la
  livraison dit que la branche a changé ;
- `tete_pr` rend `None` sans GitHub.
"""
from pathlib import Path

import pytest
from unittest.mock import AsyncMock, MagicMock

import aiosqlite

from tessera.models.ticket import TicketStatus
from tessera.services.database import create_run, init_db
from tessera.services.github_workflow import GitHubWorkflowService
from tessera.services.livraison import Livraison
from tessera.services.orchestrator import Orchestrator
from tessera.services.pipeline_approbation import suivre_documentation
from tessera.services.pipeline_events import (
    EventType,
    OrchestratorEvent,
    PipelineResult,
)
from tessera.services.sha_approbation import (
    noter_approbation,
    noter_poussee,
    sha_pousse_du_ticket,
)

_A = "a" * 40
_B = "b" * 40
_C = "c" * 40


async def _colonne(db_path: Path, colonne: str, run_id: str) -> str | None:
    async with aiosqlite.connect(str(db_path)) as db:
        async with db.execute(
            f"SELECT {colonne} FROM pipeline_runs WHERE id=?", (run_id,)
        ) as cursor:
            ligne = await cursor.fetchone()
    assert ligne is not None
    return None if ligne[0] is None else str(ligne[0])


async def test_shas_are_written_on_the_run_row(tmp_path: Path) -> None:
    db = tmp_path / "ide.db"
    await init_db(db)
    run_id = await create_run(db, "proj", "ticket-001")

    await noter_approbation(db, run_id, _A)
    await noter_poussee(db, run_id, _B)

    assert await _colonne(db, "approved_sha", run_id) == _A
    assert await _colonne(db, "pushed_sha", run_id) == _B


async def test_pushed_sha_of_ticket_is_the_latest_one(tmp_path: Path) -> None:
    db = tmp_path / "ide.db"
    await init_db(db)
    assert await sha_pousse_du_ticket(db, "proj", "ticket-001") is None
    ancien = await create_run(db, "proj", "ticket-001")
    await noter_poussee(db, ancien, _A)
    recent = await create_run(db, "proj", "ticket-001")
    await noter_poussee(db, recent, _B)
    sans_push = await create_run(db, "proj", "ticket-001")
    await noter_approbation(db, sans_push, _C)
    await create_run(db, "proj", "ticket-002")

    assert await sha_pousse_du_ticket(db, "proj", "ticket-001") == _B
    assert await sha_pousse_du_ticket(db, "autre", "ticket-001") is None


def _orch(tmp_path: Path, tetes: list[str]) -> Orchestrator:
    espace = AsyncMock()
    espace.head_sha.side_effect = tetes
    orch = Orchestrator(
        runner=MagicMock(),
        ticket_service=AsyncMock(),
        project_context="ctx",
        agent_configs=[],
        pipeline_log_path=tmp_path / "memory" / "log.md",
        git_workspace=espace,
    )
    orch._run_recorder = AsyncMock()
    return orch


def _resultat(approved_sha: str | None) -> PipelineResult:
    return PipelineResult(
        ticket_id="ticket-001",
        final_status=TicketStatus.done,
        rounds=1,
        approved=True,
        approved_sha=approved_sha,
        run_id="run-1",
    )


async def test_approved_sha_follows_the_documentation_commit(tmp_path: Path) -> None:
    orch = _orch(tmp_path, [_B])

    suite = await suivre_documentation(orch, _resultat(_A), _A)

    assert suite.approved_sha == _B
    orch._run_recorder.noter_approbation.assert_awaited_once_with("run-1", _B)  # type: ignore[union-attr]


async def test_approved_sha_stays_if_head_had_moved_before_documentation(
    tmp_path: Path,
) -> None:
    orch = _orch(tmp_path, [_C])

    suite = await suivre_documentation(orch, _resultat(_A), _B)

    assert suite.approved_sha == _A
    orch._run_recorder.noter_approbation.assert_not_awaited()  # type: ignore[union-attr]


async def test_approved_sha_stays_without_documentation_commit(tmp_path: Path) -> None:
    orch = _orch(tmp_path, [_A])

    suite = await suivre_documentation(orch, _resultat(_A), _A)

    assert suite.approved_sha == _A
    orch._run_recorder.noter_approbation.assert_not_awaited()  # type: ignore[union-attr]


async def test_unapproved_result_is_left_alone(tmp_path: Path) -> None:
    orch = _orch(tmp_path, [])

    suite = await suivre_documentation(orch, _resultat(None), None)

    assert suite.approved_sha is None


async def test_changed_branch_blocks_the_ticket(tmp_path: Path) -> None:
    orch = _orch(tmp_path, [])
    evenements: list[OrchestratorEvent] = []

    async def collecte(event: OrchestratorEvent) -> None:
        evenements.append(event)

    livraison = Livraison(
        branche_modifiee=True,
        arret="la branche a changé depuis l'approbation : bad0bad",
    )

    resultat = await orch._bloquer_branche_modifiee(
        _resultat(_A), livraison, "proj", collecte
    )

    assert resultat.final_status is TicketStatus.blocked
    assert resultat.arret == livraison.arret
    assert [e.type for e in evenements] == [EventType.TICKET_STATUS_CHANGED]
    assert evenements[0].data["status"] == TicketStatus.blocked.value


async def test_head_of_pull_request_is_none_without_github() -> None:
    workflow = GitHubWorkflowService(
        git_workspace=None, github=None, base_branch="main"
    )

    assert await workflow.tete_pr(7) is None


async def test_watcher_check_reads_the_sha_noted_by_the_delivery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The real chain: pushed SHA noted after phase 1, read back for the watcher."""
    from tessera.config import settings
    from tessera.routers.orchestrator import _controle_tete_de, _noter_sha_pousse

    db = tmp_path / "ide.db"
    monkeypatch.setattr(settings, "ide_db_path", db)
    await init_db(db)
    run_id = await create_run(db, "proj", "ticket-001")
    resultat = _resultat(_A).model_copy(update={"run_id": run_id})
    # Le rebase du pipeline a réécrit la tête : `_B` n'est pas `approved_sha`.
    await _noter_sha_pousse(resultat, Livraison(pushed_sha=_B))

    async def lire(pr_number: int) -> str | None:
        return _B

    controle = await _controle_tete_de("proj", "ticket-001", lire)

    assert controle.pushed_sha == _B
    assert await controle.lire_tete(7) == _B
