"""The shared test slot re-reads its limit at each acquisition (ticket-807)."""
import asyncio

import pytest

from tessera.config import settings
from tessera.services.limiteur_de_suites import LimiteurDeSuites


async def _laisser_tourner() -> None:
    await asyncio.sleep(0.01)


async def test_a_lowered_limit_applies_to_the_next_acquisition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "max_parallel_test_runs", 3)
    limiteur = LimiteurDeSuites()
    await limiteur.acquire()
    await limiteur.acquire()
    monkeypatch.setattr(settings, "max_parallel_test_runs", 2)

    tache = asyncio.create_task(limiteur.acquire())
    await _laisser_tourner()
    assert not tache.done()
    limiteur.release()
    await asyncio.wait_for(tache, 1)  # un créneau libre, la limite tient
    assert limiteur.libre() is False


async def test_a_slot_held_before_the_change_is_kept(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "max_parallel_test_runs", 3)
    limiteur = LimiteurDeSuites()
    for _ in range(3):
        await limiteur.acquire()
    monkeypatch.setattr(settings, "max_parallel_test_runs", 1)

    assert limiteur.tenus() == 3  # personne n'est évincé
    limiteur.release()
    limiteur.release()
    assert limiteur.libre() is False  # un seul tenu, limite 1
    limiteur.release()
    assert limiteur.libre() is True


async def test_a_limit_of_zero_in_env_still_means_no_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "max_parallel_test_runs", 0)
    limiteur = LimiteurDeSuites()
    for _ in range(20):
        await asyncio.wait_for(limiteur.acquire(), 1)
    assert limiteur.libre() is True


async def test_a_forced_limit_wins_over_the_setting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "max_parallel_test_runs", 5)
    limiteur = LimiteurDeSuites(limite=1)
    await limiteur.acquire()
    assert limiteur.libre() is False
