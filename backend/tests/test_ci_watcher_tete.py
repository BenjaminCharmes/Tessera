"""CIWatcher refuse de merger une PR dont la tête a bougé — ticket-492.

Couverture :
- tête de la PR différente du SHA poussé → phase 2 jamais appelée, ticket blocked,
  ci_merge_done(merged=False), attendre_merge à False ;
- SHA poussé inconnu → même refus (échec fermé, ADR-039) ;
- tête illisible ou absente → même refus ;
- tête égale au SHA poussé → la phase 2 tourne et le merge suit ;
- après un rebase du pipeline, le SHA poussé mis à jour laisse passer le merge.
"""
import asyncio

from tessera.models.ticket import TicketStatus
from tessera.services.ci_watcher import CIWatcher, ControleTete
from tessera.services.livraison import Livraison
from tessera.services.pipeline_events import EventType, OrchestratorEvent

_SHA_POUSSE = "a" * 40
_SHA_REBASE = "b" * 40
_SHA_INTRUS = "c" * 40


class _Phase2:
    def __init__(self) -> None:
        self.appels = 0

    async def __call__(self, pr_number: int) -> Livraison:
        self.appels += 1
        return Livraison(pr_number=pr_number, merged=True)


def _tete(valeur: str | None) -> ControleTete:
    async def lire(pr_number: int) -> str | None:
        return valeur

    return ControleTete(pushed_sha=_SHA_POUSSE, lire_tete=lire)


async def _surveiller(
    controle: ControleTete,
) -> tuple[bool, _Phase2, list[OrchestratorEvent]]:
    watcher = CIWatcher()
    phase2 = _Phase2()
    events: list[OrchestratorEvent] = []

    async def collect(event: OrchestratorEvent) -> None:
        events.append(event)

    await watcher.surveiller(
        "proj", "ticket-001", 7, phase2, collect, controle_tete=controle
    )
    merge = await asyncio.wait_for(watcher.attendre_merge("proj", "ticket-001"), 5.0)
    return merge, phase2, events


def _types(events: list[OrchestratorEvent]) -> list[EventType]:
    return [e.type for e in events]


async def test_changed_head_blocks_ticket_and_skips_merge() -> None:
    merge, phase2, events = await _surveiller(_tete(_SHA_INTRUS))

    assert merge is False
    assert phase2.appels == 0
    statuts = [e for e in events if e.type is EventType.TICKET_STATUS_CHANGED]
    assert [e.data["status"] for e in statuts] == [TicketStatus.blocked.value]
    done = [e for e in events if e.type is EventType.CI_MERGE_DONE]
    assert done[0].data["merged"] is False
    assert "reste ouverte" in done[0].data["arret"]
    assert "#7" in done[0].data["arret"]


async def test_unknown_pushed_sha_refuses_merge() -> None:
    async def lire(pr_number: int) -> str | None:
        return _SHA_POUSSE

    controle = ControleTete(pushed_sha=None, lire_tete=lire)
    merge, phase2, events = await _surveiller(controle)

    assert merge is False
    assert phase2.appels == 0
    assert EventType.TICKET_STATUS_CHANGED in _types(events)


async def test_unreadable_head_refuses_merge() -> None:
    async def lire(pr_number: int) -> str | None:
        raise RuntimeError("GitHub injoignable")

    merge, phase2, _ = await _surveiller(
        ControleTete(pushed_sha=_SHA_POUSSE, lire_tete=lire)
    )

    assert merge is False
    assert phase2.appels == 0


async def test_missing_head_refuses_merge() -> None:
    merge, phase2, _ = await _surveiller(_tete(None))

    assert merge is False
    assert phase2.appels == 0


async def test_same_head_lets_the_merge_through() -> None:
    merge, phase2, events = await _surveiller(_tete(_SHA_POUSSE))

    assert merge is True
    assert phase2.appels == 1
    done = [e for e in events if e.type is EventType.CI_MERGE_DONE]
    assert done[0].data["merged"] is True


async def test_updated_pushed_sha_after_pipeline_rebase_merges() -> None:
    """A rebase done by the pipeline moves `pushed_sha`: the new head is the one."""

    async def lire(pr_number: int) -> str | None:
        return _SHA_REBASE

    ancien = ControleTete(pushed_sha=_SHA_POUSSE, lire_tete=lire)
    merge_avant, _, _ = await _surveiller(ancien)
    assert merge_avant is False

    apres = ControleTete(pushed_sha=_SHA_REBASE, lire_tete=lire)
    merge_apres, phase2, _ = await _surveiller(apres)
    assert merge_apres is True
    assert phase2.appels == 1
