"""CIWatcher — tâche de fond pour la CI et le merge — ticket-306.

Couverture :
- Une seconde livraison du même projet attend la première.
- Deux projets différents ne s'attendent pas.
- CI verte → merge, ci_merge_done avec merged=True.
- CI rouge → ticket blocked, ci_merge_done avec merged=False et arret contenant le numéro de PR.
- en_attente liste le ticket pendant l'attente, plus après ci_merge_done.
- Arrêt : les tâches en cours sont annulées sans lever d'exception.
"""
import asyncio
from collections.abc import Awaitable, Callable

from tessera.models.ticket import TicketStatus
from tessera.services.ci_watcher import CIWatcher
from tessera.services.livraison import Livraison
from tessera.services.pipeline_events import EventType, OrchestratorEvent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _rien(event: OrchestratorEvent) -> None:
    """No-op event callback."""


async def _phase2_success(pr_number: int) -> Livraison:
    return Livraison(pr_number=pr_number, merged=True)


async def _phase2_red_ci(pr_number: int) -> Livraison:
    return Livraison(
        pr_number=pr_number,
        merged=False,
        arret=f"CI failing : la PR #{pr_number} reste ouverte.",
    )


def _collecteur() -> tuple[
    list[OrchestratorEvent],
    Callable[[OrchestratorEvent], Awaitable[None]],
]:
    """Returns (events_list, callback) to collect emitted events."""
    events: list[OrchestratorEvent] = []

    async def collect(event: OrchestratorEvent) -> None:
        events.append(event)

    return events, collect


# ---------------------------------------------------------------------------
# Sérialisation par projet
# ---------------------------------------------------------------------------


async def test_seconde_livraison_meme_projet_attend_la_premiere() -> None:
    """A second delivery for the same project waits for the first to finish."""
    watcher = CIWatcher()
    ordre: list[str] = []
    gate = asyncio.Event()

    async def phase2_sequentielle(pr_number: int) -> Livraison:
        await gate.wait()
        ordre.append(f"pr{pr_number}")
        return Livraison(pr_number=pr_number, merged=True)

    events, collect = _collecteur()

    await watcher.surveiller("proj", "ticket-001", 1, phase2_sequentielle, collect)
    await watcher.surveiller("proj", "ticket-002", 2, phase2_sequentielle, collect)

    # Pendant l'attente, les deux tickets sont inscrits.
    await asyncio.sleep(0)
    assert set(watcher.en_attente("proj")) == {"ticket-001", "ticket-002"}

    gate.set()
    await asyncio.sleep(0.05)

    # Ordre séquentiel : ticket-001 avant ticket-002.
    assert ordre == ["pr1", "pr2"]

    done = [e for e in events if e.type is EventType.CI_MERGE_DONE]
    assert len(done) == 2
    assert done[0].data["ticket_id"] == "ticket-001"
    assert done[1].data["ticket_id"] == "ticket-002"


async def test_deux_projets_differents_ne_s_attendent_pas() -> None:
    """Two different projects run their deliveries concurrently."""
    watcher = CIWatcher()
    en_cours: list[str] = []
    max_concurrence: list[int] = []

    def _faire_phase2(project_id: str) -> Callable[[int], Awaitable[Livraison]]:
        async def _phase2(pr_number: int) -> Livraison:
            en_cours.append(project_id)
            max_concurrence.append(len(en_cours))
            await asyncio.sleep(0.01)
            en_cours.remove(project_id)
            return Livraison(pr_number=pr_number, merged=True)

        return _phase2

    await watcher.surveiller("proj-a", "ticket-001", 1, _faire_phase2("proj-a"), _rien)
    await watcher.surveiller("proj-b", "ticket-002", 2, _faire_phase2("proj-b"), _rien)

    await asyncio.sleep(0.05)

    # Les deux ont tourné en même temps (concurrence maximale = 2).
    assert max(max_concurrence) == 2


# ---------------------------------------------------------------------------
# CI verte → merge
# ---------------------------------------------------------------------------


async def test_ci_verte_emet_ci_merge_done_merged_true() -> None:
    """Green CI emits ci_merge_done with merged=True and arret=None."""
    watcher = CIWatcher()
    events, collect = _collecteur()

    await watcher.surveiller("proj", "ticket-001", 42, _phase2_success, collect)
    await asyncio.sleep(0.05)

    done = [e for e in events if e.type is EventType.CI_MERGE_DONE]
    assert len(done) == 1
    assert done[0].data["merged"] is True
    assert done[0].data["arret"] is None
    assert done[0].data["pr_number"] == 42
    assert done[0].data["project_id"] == "proj"
    assert done[0].data["ticket_id"] == "ticket-001"


# ---------------------------------------------------------------------------
# CI rouge → blocked
# ---------------------------------------------------------------------------


async def test_ci_rouge_emet_ticket_blocked_et_ci_merge_done_merged_false() -> None:
    """Red CI emits ticket_status_changed(blocked) then ci_merge_done(merged=False)."""
    watcher = CIWatcher()
    events, collect = _collecteur()

    await watcher.surveiller("proj", "ticket-001", 7, _phase2_red_ci, collect)
    await asyncio.sleep(0.05)

    status_events = [e for e in events if e.type is EventType.TICKET_STATUS_CHANGED]
    assert len(status_events) == 1
    assert status_events[0].data["status"] == TicketStatus.blocked.value

    done = [e for e in events if e.type is EventType.CI_MERGE_DONE]
    assert len(done) == 1
    assert done[0].data["merged"] is False
    # L'arret contient le numéro de la PR.
    assert "7" in done[0].data["arret"]
    assert done[0].data["pr_number"] == 7


# ---------------------------------------------------------------------------
# en_attente
# ---------------------------------------------------------------------------


async def test_en_attente_liste_le_ticket_pendant_l_attente_puis_plus_apres() -> None:
    """en_attente lists the ticket during the wait, then removes it after ci_merge_done."""
    watcher = CIWatcher()
    gate = asyncio.Event()

    async def phase2_bloquante(pr_number: int) -> Livraison:
        await gate.wait()
        return Livraison(pr_number=pr_number, merged=True)

    await watcher.surveiller("proj", "ticket-001", 1, phase2_bloquante, _rien)
    await asyncio.sleep(0)

    # Pendant l'attente : listé.
    assert "ticket-001" in watcher.en_attente("proj")

    gate.set()
    await asyncio.sleep(0.05)

    # Après ci_merge_done : retiré.
    assert "ticket-001" not in watcher.en_attente("proj")


async def test_en_attente_projet_inconnu_retourne_tuple_vide() -> None:
    watcher = CIWatcher()
    assert watcher.en_attente("projet-inconnu") == ()


# ---------------------------------------------------------------------------
# Arrêt
# ---------------------------------------------------------------------------


async def test_arret_annule_les_taches_sans_lever() -> None:
    """arreter() cancels running tasks without raising any exception."""
    watcher = CIWatcher()
    started = asyncio.Event()

    async def phase2_infinie(pr_number: int) -> Livraison:
        started.set()
        await asyncio.sleep(3600)
        return Livraison(pr_number=pr_number, merged=True)

    await watcher.surveiller("proj", "ticket-001", 1, phase2_infinie, _rien)
    await started.wait()

    # Ne doit pas lever d'exception.
    await watcher.arreter()

    # Après l'arrêt, plus de tâches actives.
    assert len(watcher._taches) == 0
