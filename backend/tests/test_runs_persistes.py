"""Chaque ticket d'une file ou d'un run autonome laisse une ligne en base — ticket-121.

`run_queue`, `run_autonomous` et `/chat/run` appelaient `run_pipeline` sans
`run_id` : aucun cout persiste dans `agent_calls`, aucun `create_run` /
`finish_run`. La ventilation des couts ignorait les modes qui coutent le plus.
"""
import asyncio
import time
from pathlib import Path

import aiosqlite
import pytest
from fastapi.testclient import TestClient

from tests.test_providers_base import FakeProvider
from tessera.config import settings
from tessera.main import app
from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services.agent_registry import AgentRegistryService
from tessera.services.agent_runner import AgentRunner
from tessera.services.database import init_db
from tessera.services.orchestrator import Orchestrator
from tessera.services.run_recorder import RunRecorder


def _ticket(tid: str) -> Ticket:
    return Ticket(
        id=tid, title=f"Ticket {tid}", type=TicketType.feat,
        status=TicketStatus.todo, priority=TicketPriority.medium,
        agent="codeur", body="Fais-le.",
    )


class _Tickets:
    def __init__(self, *ids: str) -> None:
        self._tickets = {tid: _ticket(tid) for tid in ids}

    async def get_ticket(self, ticket_id: str) -> Ticket | None:
        return self._tickets.get(ticket_id)

    async def update_status(self, ticket_id: str, status: TicketStatus) -> Ticket:
        ticket = self._tickets[ticket_id]
        ticket.status = status
        return ticket

    async def list_tickets(self, status: TicketStatus | None = None) -> list[Ticket]:
        return [t for t in self._tickets.values() if status is None or t.status is status]


class _Git:
    async def commit_bookkeeping(self) -> None:
        pass

    async def is_clean(self) -> bool:
        return True

    async def initialiser_base_ref(
        self, base_branch: str | None = None, *, exiger_distant: bool = False
    ) -> str | None:
        return None

    async def create_branch(self, ticket_id: str, slug: str) -> str:
        return f"{ticket_id}-slug"

    async def current_diff(self) -> str:
        return "diff --git a/x b/x\n+1\n"

    async def diff_depuis_base(self) -> str:
        return "diff --git a/x b/x\n+1\n"

    async def commit_all(self, message: str) -> str | None:
        return "abc1234"

    async def advance_base_ref(self) -> None:
        return None


def _orchestrateur(tmp_path: Path, db_path: Path, tickets: _Tickets) -> Orchestrator:
    prompts = tmp_path / "prompts"
    prompts.mkdir(exist_ok=True)
    for role in ("codeur", "reviewer"):
        (prompts / f"{role}.md").write_text(f"Tu es le {role}.", encoding="utf-8")
    # Le reviewer approuve du premier coup : le meme contenu sert au codeur.
    runner = AgentRunner(
        FakeProvider(content="APPROVED"), AgentRegistryService(prompts), db_path=db_path
    )
    return Orchestrator(
        runner=runner,
        ticket_service=tickets,  # type: ignore[arg-type]
        project_context="ctx",
        agent_configs=[],
        pipeline_log_path=tmp_path / "log.md",
        git_workspace=_Git(),  # type: ignore[arg-type]
        run_recorder=RunRecorder(db_path),
    )


async def _runs(db_path: Path) -> list[tuple[str, str, str | None]]:
    async with aiosqlite.connect(str(db_path)) as db:
        async with db.execute(
            "SELECT id, ticket_id, finished_at FROM pipeline_runs ORDER BY started_at"
        ) as cursor:
            return [(str(r[0]), str(r[1]), r[2]) for r in await cursor.fetchall()]


async def _run_ids_des_appels(db_path: Path) -> set[str]:
    async with aiosqlite.connect(str(db_path)) as db:
        async with db.execute("SELECT DISTINCT run_id FROM agent_calls") as cursor:
            return {str(r[0]) for r in await cursor.fetchall()}


async def test_run_queue_ecrit_une_ligne_par_ticket_et_ses_appels_la_portent(
    tmp_path: Path,
) -> None:
    # Sans `run_id`, `AgentRunner` calculait le cout et ne l'ecrivait nulle
    # part : l'onglet Couts ne voyait que les runs lances un par un.
    db_path = tmp_path / "tessera.db"
    await init_db(db_path)
    tickets = _Tickets("ticket-001", "ticket-002")

    resultats = await _orchestrateur(tmp_path, db_path, tickets).run_queue(
        "p", ["ticket-001", "ticket-002"]
    )

    assert [r.approved for r in resultats] == [True, True]
    runs = await _runs(db_path)
    assert [ticket for _, ticket, _ in runs] == ["ticket-001", "ticket-002"]
    assert all(fin is not None for _, _, fin in runs), "chaque run doit etre clos"
    assert await _run_ids_des_appels(db_path) == {run_id for run_id, _, _ in runs}


async def test_run_autonomous_ecrit_une_ligne_par_ticket(tmp_path: Path) -> None:
    db_path = tmp_path / "tessera.db"
    await init_db(db_path)
    tickets = _Tickets("ticket-001", "ticket-002")

    await _orchestrateur(tmp_path, db_path, tickets).run_autonomous("p", max_tickets=2)

    runs = await _runs(db_path)
    assert sorted(ticket for _, ticket, _ in runs) == ["ticket-001", "ticket-002"]
    assert all(fin is not None for _, _, fin in runs)


async def test_un_run_id_fourni_par_l_appelant_n_est_pas_double(tmp_path: Path) -> None:
    # `/orchestrator/run` et le stream single ouvrent deja leur run pour y
    # rattacher les evenements : l'orchestrateur ne doit pas en ouvrir un
    # second, ni clore celui qu'il n'a pas ouvert.
    db_path = tmp_path / "tessera.db"
    await init_db(db_path)
    tickets = _Tickets("ticket-001")
    orch = _orchestrateur(tmp_path, db_path, tickets)
    run_id = await RunRecorder(db_path).ouvrir("p", "ticket-001")

    async def _noop(event: object) -> None:
        return None

    await orch.run_pipeline("p", "ticket-001", _noop, run_id=run_id)

    runs = await _runs(db_path)
    assert [r[0] for r in runs] == [run_id]
    assert runs[0][2] is None, "clore appartient a celui qui a ouvert"


# ------------------------------------------------------------------
# Le stream ferme le run en base sur toute exception, pas seulement ValueError
# ------------------------------------------------------------------


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ws = tmp_path / "workspace"
    project = ws / "mon-projet"
    (project / "memory").mkdir(parents=True)
    (project / "CLAUDE.md").write_text("# mon-projet\n", encoding="utf-8")
    for status in ("todo", "in-progress", "in-review", "done", "blocked"):
        (project / "tickets" / status).mkdir(parents=True)
    db_path = tmp_path / "tessera.db"
    asyncio.run(init_db(db_path))
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    monkeypatch.setattr(settings, "ide_db_path", db_path)
    monkeypatch.setattr(settings, "llm_provider", "agent_sdk")
    return ws


async def _runs_ouverts(db_path: Path) -> int:
    async with aiosqlite.connect(str(db_path)) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM pipeline_runs WHERE finished_at IS NULL"
        ) as cursor:
            row = await cursor.fetchone()
    return int(row[0]) if row else 0


def test_une_panne_inattendue_clot_le_run_en_base(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Le stream n'attrapait que `ValueError` : toute autre exception sautait
    # `finish_run`, et l'historique affichait « en cours » pour toujours.
    # Depuis ticket-128 c'est l'executeur qui porte cette garantie, dans son
    # `finally` — la tache n'a plus d'appelant pour rattraper quoi que ce soit.
    class _OrchestrateurQuiCasse:
        async def run_pipeline(
            self,
            project_id: str,
            ticket_id: str,
            on_event: object,
            run_id: str | None = None,
            dialogue: object = None,
        ) -> object:
            raise RuntimeError("panne inattendue")

    async def _build(project_id: str) -> _OrchestrateurQuiCasse:
        return _OrchestrateurQuiCasse()

    monkeypatch.setattr("tessera.routers.orchestrator._build_orchestrator", _build)

    with TestClient(app) as client:
        with client.websocket_connect("/api/v1/orchestrator/observe") as ws:
            resp = client.post(
                "/api/v1/orchestrator/run",
                json={"project_id": "mon-projet", "ticket_id": "ticket-001"},
            )
            assert resp.status_code == 202
            vu = None
            for _ in range(60):
                message = ws.receive_json()
                if message.get("type") == "error":
                    vu = message
                if message.get("type") == "run_closed":
                    break
            assert vu is not None and "panne inattendue" in vu["data"]["error"]

    for _ in range(50):
        if asyncio.run(_runs_ouverts(settings.ide_db_path)) == 0:
            break
        time.sleep(0.05)
    assert asyncio.run(_runs_ouverts(settings.ide_db_path)) == 0


async def test_l_orchestrateur_construit_par_le_routeur_enregistre_ses_runs(
    workspace: Path,
) -> None:
    # C'est par la que passent `/chat/run`, la file et le run autonome.
    from tessera.routers.orchestrator import _build_orchestrator

    orchestrator = await _build_orchestrator("mon-projet")

    assert isinstance(orchestrator._run_recorder, RunRecorder)
