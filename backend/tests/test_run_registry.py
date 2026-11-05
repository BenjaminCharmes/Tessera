"""`RunRegistry.projet_tenu_par_file` — ticket-850 (ADR-080, ADR-034)."""
import pytest

from tessera.services.pipeline.run_registry import RunRegistry


async def test_queue_holds_project_between_two_tickets() -> None:
    registry = RunRegistry()
    async with registry.acquire("demo", mode="queue") as run:
        # Fin d'un ticket, début du suivant : le run de la file n'a pas bougé.
        for ticket_id in ("ticket-001", None, "ticket-002"):
            registry.mettre_a_jour(run.run_id, ticket_id=ticket_id)
            assert registry.projet_tenu_par_file("demo")
        assert not registry.projet_tenu_par_file("autre")


async def test_queue_releases_project_when_it_closes() -> None:
    registry = RunRegistry()
    assert not registry.projet_tenu_par_file("demo")
    async with registry.acquire("demo", mode="queue"):
        assert registry.projet_tenu_par_file("demo")
    assert not registry.projet_tenu_par_file("demo")


async def test_queue_releases_project_on_exception() -> None:
    registry = RunRegistry()
    with pytest.raises(RuntimeError):
        async with registry.acquire("demo", mode="queue"):
            raise RuntimeError("panne en pleine file")
    assert not registry.projet_tenu_par_file("demo")


async def test_single_run_is_not_a_queue() -> None:
    registry = RunRegistry()
    async with registry.acquire("demo", "ticket-001", mode="single"):
        assert registry.projet_occupe("demo")
        assert not registry.projet_tenu_par_file("demo")


async def test_autonomous_mode_counts_as_a_queue() -> None:
    registry = RunRegistry()
    async with registry.acquire("demo", mode="autonomous"):
        assert registry.projet_tenu_par_file("demo")
    assert not registry.projet_tenu_par_file("demo")
