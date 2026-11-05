"""Reading history for the anomaly detector — tickets 836 to 838 (ADR-078)."""
import sqlite3
from pathlib import Path

from tessera.services import database
from tessera.services.anomalies.lecture_evenements import evenements_de_etapes
from tessera.services.anomalies.lecture_historique import durees_passees
from tessera.services.database import init_db
from tests.anomalies_base import base_neuve, evenement, ligne_de_run


def _ts(i: int, secondes: int = 0) -> str:
    jour = 1 + i // 20
    return f"2026-11-{jour:02d}T{i % 20:02d}:{secondes // 60:02d}:{secondes % 60:02d}+00:00"


async def _etape_close(db: Path, run: str, i: int, duree_s: int, ticket: str = "ticket-001") -> None:
    await evenement(db, run, "test_started", ts=_ts(i), ticket_id=ticket)
    await evenement(db, run, "test_result", ts=_ts(i, duree_s), ticket_id=ticket)


async def test_evenements_de_etapes_reads_stage_events_only_of_the_ticket(tmp_path: Path) -> None:
    db = await base_neuve(tmp_path / "t.db")
    await ligne_de_run(db, "r")
    await evenement(db, "r", "agent_token", ts=_ts(0))
    await evenement(db, "r", "agent_tool_use", ts=_ts(0), data={"tool": "X"})
    await evenement(db, "r", "test_started", ts=_ts(1))
    await evenement(db, "r", "test_started", ts=_ts(2), ticket_id="autre")
    lus = await evenements_de_etapes(db, "r", "ticket-001")
    assert [e.type for e in lus] == ["test_started"]


async def test_durees_passees_returns_the_20_most_recent_closed_stages_of_the_project(
    tmp_path: Path,
) -> None:
    db = await base_neuve(tmp_path / "t.db")
    await ligne_de_run(db, "r1")
    await ligne_de_run(db, "r2", project_id="autre")
    for i in range(21):  # durée = 100 + i : la plus ancienne (100) doit sortir
        await _etape_close(db, "r1", i, 100 + i)
    await _etape_close(db, "r2", 5, 7)  # un autre projet
    await evenement(db, "r1", "test_started", ts=_ts(30))  # abandonnée par la suivante
    await evenement(db, "r1", "test_started", ts=_ts(31), ticket_id="ticket-002")  # ouverte
    await evenement(db, "r1", "test_started", ts=_ts(32))
    durees = await durees_passees(db, "p", "tests")
    assert len(durees) == 20
    assert durees == [float(100 + i) for i in range(20, 0, -1)]


async def test_durees_passees_excludes_an_abandoned_stage(tmp_path: Path) -> None:
    db = await base_neuve(tmp_path / "t.db")
    await ligne_de_run(db, "r")
    await evenement(db, "r", "test_started", ts=_ts(0))
    await evenement(db, "r", "test_started", ts=_ts(1))
    await evenement(db, "r", "test_result", ts=_ts(1, 30))
    assert await durees_passees(db, "p", "tests") == [30.0]


async def test_durees_passees_reads_agent_stages_by_agent(tmp_path: Path) -> None:
    db = await base_neuve(tmp_path / "t.db")
    await ligne_de_run(db, "r")
    await evenement(db, "r", "agent_started", ts=_ts(0), agent="codeur")
    await evenement(db, "r", "agent_done", ts=_ts(0, 90), agent="codeur")
    await evenement(db, "r", "agent_started", ts=_ts(1), agent="reviewer")
    await evenement(db, "r", "agent_done", ts=_ts(1, 30), agent="reviewer")
    assert await durees_passees(db, "p", "codeur") == [90.0]


async def test_durees_passees_pairs_per_ticket_inside_a_queue_envelope(tmp_path: Path) -> None:
    db = await base_neuve(tmp_path / "t.db")
    await ligne_de_run(db, "env", mode="queue", ticket_id="queue")
    await evenement(db, "env", "test_started", ts=_ts(0), ticket_id="a")
    await evenement(db, "env", "test_started", ts=_ts(1), ticket_id="b")
    await evenement(db, "env", "test_result", ts=_ts(1, 40), ticket_id="b")
    await evenement(db, "env", "test_result", ts=_ts(0, 50), ticket_id="a")
    assert sorted(await durees_passees(db, "p", "tests")) == [40.0, 50.0]


async def test_agent_events_index_exists_and_init_db_stays_idempotent(tmp_path: Path) -> None:
    neuve = tmp_path / "neuve.db"
    await init_db(neuve)
    await init_db(neuve)

    ancienne = tmp_path / "ancienne.db"
    c = sqlite3.connect(str(ancienne))
    c.executescript(database._CREATE_TABLES)
    for migration in database._MIGRATIONS[:-1]:
        c.executescript(migration)
    c.execute(f"PRAGMA user_version = {len(database._MIGRATIONS) - 1}")
    c.commit()
    c.close()
    await init_db(ancienne)

    for chemin in (neuve, ancienne):
        indexes = {
            r[1] for r in sqlite3.connect(str(chemin)).execute("PRAGMA index_list(agent_events)")
        }
        assert "idx_ae_type_id" in indexes
