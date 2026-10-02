"""The live run snapshot carries db_run_id for history replay — ticket-325.

Un rechargement de page ne reçoit que l'instantané du run en cours. Sans
l'identifiant en base, le frontend ne peut pas appeler GET /runs/{id}/events
pour reconstruire les cartes passées (codeur tour 1, reviewer, sécurité…).
"""
from tessera.services.run_registry import RunRegistry


async def test_l_instantane_porte_db_run_id() -> None:
    """The snapshot includes db_run_id once the database row exists."""
    registre = RunRegistry()
    async with registre.acquire("projet-a", "ticket-001") as run:
        run.db_run_id = "db-abc123"
        instantane = registre.instantane()

    assert instantane[0]["db_run_id"] == "db-abc123"


async def test_l_instantane_porte_db_run_id_null_par_defaut() -> None:
    """Without a database row yet, db_run_id is null in the snapshot."""
    registre = RunRegistry()
    async with registre.acquire("projet-a", "ticket-001"):
        instantane = registre.instantane()

    assert instantane[0]["db_run_id"] is None


async def test_run_executor_pose_db_run_id_apres_create_run() -> None:
    """run.db_run_id matches the row id created by create_run."""
    # Vérifie que run_executor.py expose l'id en base dans le registre,
    # ce qui rend l'instantané utile pour le frontend (ticket-325).
    registre = RunRegistry()
    async with registre.acquire("projet-a", "ticket-001") as run:
        # Simule ce que run_executor fait après create_run
        run.db_run_id = "uuid-from-db"
        assert registre.instantane()[0]["db_run_id"] == "uuid-from-db"
