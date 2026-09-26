"""A killed backend no longer leaves its runs "in progress" forever — ticket-177.

Un backend redémarré pendant une file laissait deux lignes ouvertes en base,
`finished_at` à null, pour toujours. `RunRegistry` vit en mémoire et se vide ;
c'est la base qui gardait les lignes.
"""
from pathlib import Path

import aiosqlite

from tessera.services.database import (
    CAUSE_RUN_ORPHELIN,
    create_run,
    finish_run,
    init_db,
    save_agent_call,
    save_event,
    solder_les_runs_orphelins,
)


async def _base(tmp_path: Path) -> Path:
    db = tmp_path / "t.db"
    await init_db(db)
    return db


async def test_un_run_sans_fin_est_solde_en_blocked_avec_sa_cause(tmp_path: Path) -> None:
    db = await _base(tmp_path)
    run_id = await create_run(db, "p", "ticket-001")

    soldes = await solder_les_runs_orphelins(db)

    assert soldes == [run_id]
    async with aiosqlite.connect(db) as conn:
        async with conn.execute(
            "SELECT finished_at, approved, final_status FROM pipeline_runs WHERE id=?", (run_id,)
        ) as cur:
            finished_at, approved, statut = await cur.fetchone()
        async with conn.execute(
            "SELECT type, data_json FROM agent_events WHERE run_id=? ORDER BY id", (run_id,)
        ) as cur:
            evenements = await cur.fetchall()
    assert finished_at is not None
    assert approved == 0
    assert statut == "blocked"
    assert evenements[-1][0] == "error"
    assert CAUSE_RUN_ORPHELIN in evenements[-1][1]


async def test_un_run_deja_fini_n_est_pas_touche(tmp_path: Path) -> None:
    db = await _base(tmp_path)
    run_id = await create_run(db, "p", "ticket-001")
    await finish_run(db, run_id, rounds=1, approved=True, final_status="done")

    assert await solder_les_runs_orphelins(db) == []
    async with aiosqlite.connect(db) as conn:
        async with conn.execute("SELECT approved, final_status FROM pipeline_runs") as cur:
            assert await cur.fetchone() == (1, "done")


async def test_le_solde_garde_les_evenements_et_les_couts(tmp_path: Path) -> None:
    # L'historique et la ventilation des coûts sont ce qu'on veut lire après
    # coup : les solder ne doit rien en effacer.
    db = await _base(tmp_path)
    run_id = await create_run(db, "p", "ticket-001")
    await save_event(db, run_id, "agent_started", "codeur", {"round": 1}, "2026-09-26T08:00:00+00:00")
    await save_agent_call(db, run_id, "ticket-001", "codeur", "m", 10, 20, 0, 0.4, 100)

    await solder_les_runs_orphelins(db)

    async with aiosqlite.connect(db) as conn:
        async with conn.execute("SELECT count(*) FROM agent_events WHERE run_id=?", (run_id,)) as cur:
            (n_events,) = await cur.fetchone()
        async with conn.execute("SELECT sum(cost_usd) FROM agent_calls WHERE run_id=?", (run_id,)) as cur:
            (cout,) = await cur.fetchone()
    assert n_events == 2
    assert cout == 0.4


async def test_le_solde_est_idempotent(tmp_path: Path) -> None:
    db = await _base(tmp_path)
    await create_run(db, "p", "ticket-001")
    assert len(await solder_les_runs_orphelins(db)) == 1
    assert await solder_les_runs_orphelins(db) == []
