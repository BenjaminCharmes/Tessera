"""CIWatcher — a ticket delivered again is bound to its new PR — ticket-874.

Coverage:
- Two watches of the same ticket (PR 1 then PR 2): the wait on PR 2 returns the
  outcome of PR 2, and PR 1 never reports.
- The ticket stays listed in `en_attente` while PR 2 is not finished.
- A result recorded for PR 1 is never read back for PR 2.
- `attendre_merge` gives up at its `timeout_s` and returns False.
"""
import asyncio

from tessera.services.livraison.ci_watcher import CIWatcher
from tessera.services.livraison.livraison import Livraison
from tessera.services.noyau.pipeline_events import EventType, OrchestratorEvent

_PLAFOND_S = 5.0


async def _rien(event: OrchestratorEvent) -> None:
    """No-op event callback."""


class _Phase2:
    """A phase 2 that ends, merged or not, once its gate is opened."""

    def __init__(self, merged: bool) -> None:
        self.gate = asyncio.Event()
        self._merged = merged

    async def __call__(self, pr_number: int) -> Livraison:
        await self.gate.wait()
        if self._merged:
            return Livraison(pr_number=pr_number, merged=True)
        return Livraison(pr_number=pr_number, merged=False, arret="CI rouge")


async def test_wait_on_second_pr_returns_the_outcome_of_the_second_pr() -> None:
    watcher = CIWatcher()
    evenements: list[OrchestratorEvent] = []

    async def collecter(event: OrchestratorEvent) -> None:
        evenements.append(event)

    premiere, seconde = _Phase2(merged=False), _Phase2(merged=True)
    await watcher.surveiller("proj", "ticket-001", 1, premiere, collecter)
    await asyncio.sleep(0.01)
    await watcher.surveiller("proj", "ticket-001", 2, seconde, collecter)

    attente = asyncio.create_task(watcher.attendre_merge("proj", "ticket-001", pr_number=2))
    await asyncio.sleep(0.01)
    seconde.gate.set()
    premiere.gate.set()

    assert await asyncio.wait_for(attente, timeout=_PLAFOND_S) is True
    finis = [e for e in evenements if e.type is EventType.CI_MERGE_DONE]
    assert [e.data["pr_number"] for e in finis] == [2]
    await watcher.arreter()


async def test_ticket_stays_listed_while_the_second_pr_is_not_finished() -> None:
    watcher = CIWatcher()
    premiere, seconde = _Phase2(merged=True), _Phase2(merged=True)
    await watcher.surveiller("proj", "ticket-001", 1, premiere, _rien)
    await asyncio.sleep(0.01)

    await watcher.surveiller("proj", "ticket-001", 2, seconde, _rien)
    await asyncio.sleep(0.01)

    assert watcher.en_attente("proj") == ("ticket-001",)
    assert watcher.prs_en_attente("proj") == (("ticket-001", 2),)

    seconde.gate.set()
    assert await asyncio.wait_for(
        watcher.attendre_merge("proj", "ticket-001", pr_number=2), _PLAFOND_S
    ) is True
    assert watcher.en_attente("proj") == ()


async def test_replacing_a_watch_that_never_started_leaves_the_ticket_listed() -> None:
    watcher = CIWatcher()
    seconde = _Phase2(merged=True)
    await watcher.surveiller("proj", "ticket-001", 1, _Phase2(merged=True), _rien)
    # Aucune cession entre les deux : la première tâche est annulée avant son premier pas.
    await watcher.surveiller("proj", "ticket-001", 2, seconde, _rien)

    assert watcher.prs_en_attente("proj") == (("ticket-001", 2),)
    assert await asyncio.wait_for(
        watcher.attendre_merge("proj", "ticket-001", pr_number=1), _PLAFOND_S
    ) is False

    seconde.gate.set()
    assert await asyncio.wait_for(
        watcher.attendre_merge("proj", "ticket-001", pr_number=2), _PLAFOND_S
    ) is True


async def test_result_of_the_first_pr_is_not_returned_for_the_second_pr() -> None:
    watcher = CIWatcher()
    watcher._suivi.noter("proj", "ticket-001", 1, True)

    # Rien n'est surveillé pour la PR 2 : elle n'hérite pas du résultat de la PR 1.
    assert await watcher.attendre_merge("proj", "ticket-001", pr_number=2) is False

    seconde = _Phase2(merged=False)
    await watcher.surveiller("proj", "ticket-001", 2, seconde, _rien)
    attente = asyncio.create_task(watcher.attendre_merge("proj", "ticket-001", pr_number=2))
    await asyncio.sleep(0.01)
    assert not attente.done()

    seconde.gate.set()
    assert await asyncio.wait_for(attente, timeout=_PLAFOND_S) is False


async def test_wait_gives_up_at_its_timeout_without_a_result() -> None:
    watcher = CIWatcher()
    await watcher.surveiller("proj", "ticket-001", 1, _Phase2(merged=True), _rien)

    merge = await asyncio.wait_for(
        watcher.attendre_merge("proj", "ticket-001", pr_number=1, timeout_s=0.05),
        _PLAFOND_S,
    )

    assert merge is False
    assert watcher.en_attente("proj") == ("ticket-001",)
    await watcher.arreter()


def test_default_wait_is_two_phase_2_and_a_margin() -> None:
    watcher = CIWatcher(timeout_phase2_s=100.0)

    assert watcher._delai_attente_s() == 260.0
