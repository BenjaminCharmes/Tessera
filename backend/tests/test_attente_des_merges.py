"""Livrer après le merge des PR précédentes de la file — ticket-533."""
import asyncio
from collections.abc import Awaitable, Callable

from tessera.models.ticket import TicketStatus
from tessera.services.attente_des_merges import (
    apres_les_merges,
    attendre_les_merges_en_cours,
)
from tessera.services.ci_watcher import CIWatcher
from tessera.services.livraison import Livraison
from tessera.services.pipeline_events import PipelineResult


class _FausseSurveillance:
    """Un `CIWatcher` réduit à ce que la livraison en lit."""

    def __init__(self, en_attente: tuple[str, ...], merges: dict[str, bool]) -> None:
        self._en_attente = en_attente
        self._merges = merges
        self.attendus: list[str] = []

    def en_attente(self, project_id: str) -> tuple[str, ...]:
        return self._en_attente

    async def attendre_merge(
        self,
        project_id: str,
        ticket_id: str,
        pr_number: int | None = None,
        etat_pr: Callable[[int], Awaitable[str]] | None = None,
    ) -> bool:
        self.attendus.append(ticket_id)
        return self._merges.get(ticket_id, True)


class _SurveillanceMuette(_FausseSurveillance):
    async def attendre_merge(
        self,
        project_id: str,
        ticket_id: str,
        pr_number: int | None = None,
        etat_pr: Callable[[int], Awaitable[str]] | None = None,
    ) -> bool:
        await asyncio.sleep(3600)
        return True


def _resultat(ticket_id: str = "ticket-2") -> PipelineResult:
    return PipelineResult(
        ticket_id=ticket_id, final_status=TicketStatus.done, rounds=1, approved=True
    )


async def test_nothing_pending_means_no_wait() -> None:
    surveillance = _FausseSurveillance((), {})

    attendus = await attendre_les_merges_en_cours(surveillance, "p", "ticket-2")

    assert attendus == ()
    assert surveillance.attendus == []


async def test_waits_for_every_earlier_ticket() -> None:
    surveillance = _FausseSurveillance(("ticket-0", "ticket-1"), {})

    attendus = await attendre_les_merges_en_cours(surveillance, "p", "ticket-2")

    assert attendus == ("ticket-0", "ticket-1")
    assert surveillance.attendus == ["ticket-0", "ticket-1"]


async def test_own_ticket_is_never_waited_for() -> None:
    surveillance = _FausseSurveillance(("ticket-2",), {})

    attendus = await attendre_les_merges_en_cours(surveillance, "p", "ticket-2")

    assert attendus == ()
    assert surveillance.attendus == []


async def test_a_blocked_earlier_ticket_does_not_stop_the_delivery() -> None:
    surveillance = _FausseSurveillance(("ticket-1",), {"ticket-1": False})

    attendus = await attendre_les_merges_en_cours(surveillance, "p", "ticket-2")

    assert attendus == ("ticket-1",)


async def test_timeout_ends_the_wait_without_raising() -> None:
    surveillance = _SurveillanceMuette(("ticket-1",), {})

    attendus = await attendre_les_merges_en_cours(
        surveillance, "p", "ticket-2", attente_max_s=0.01
    )

    assert attendus == ("ticket-1",)


async def test_delivery_starts_only_after_the_wait() -> None:
    ordre: list[str] = []
    surveillance = _FausseSurveillance(("ticket-1",), {})
    attendre = surveillance.attendre_merge

    async def attendre_et_noter(
        project_id: str,
        ticket_id: str,
        pr_number: int | None = None,
        etat_pr: Callable[[int], Awaitable[str]] | None = None,
    ) -> bool:
        ordre.append("attente")
        return await attendre(project_id, ticket_id)

    async def livrer(result: PipelineResult) -> Livraison:
        ordre.append("livraison")
        return Livraison(etapes=(), durees_ms=(), pr_number=7)

    surveillance.attendre_merge = attendre_et_noter  # type: ignore[method-assign]

    livraison = await apres_les_merges(livrer, "p", surveillance)(_resultat())

    assert ordre == ["attente", "livraison"]
    assert livraison.pr_number == 7


async def test_default_watcher_is_the_process_one() -> None:
    appels: list[str] = []

    async def livrer(result: PipelineResult) -> Livraison:
        appels.append(result.ticket_id)
        return Livraison(etapes=(), durees_ms=())

    await apres_les_merges(livrer, "projet-sans-pr-en-attente")(_resultat("ticket-9"))

    assert appels == ["ticket-9"]


async def test_real_watcher_releases_the_delivery_once_the_pr_is_done() -> None:
    watcher = CIWatcher()
    libre = asyncio.Event()

    async def phase_2(pr: int) -> Livraison:
        await libre.wait()
        return Livraison(etapes=(), durees_ms=(), pr_number=pr, merged=True)

    async def on_event(event: object) -> None:
        return None

    await watcher.surveiller("p", "ticket-1", 11, phase_2, on_event)  # type: ignore[arg-type]
    livree = asyncio.Event()

    async def livrer(result: PipelineResult) -> Livraison:
        livree.set()
        return Livraison(etapes=(), durees_ms=())

    tache = asyncio.create_task(apres_les_merges(livrer, "p", watcher)(_resultat()))
    await asyncio.sleep(0.05)
    assert not livree.is_set()

    libre.set()
    await asyncio.wait_for(tache, timeout=2)

    assert livree.is_set()
    await watcher.arreter()
