"""CIWatcher rejoue la phase 2 une fois après une erreur réseau — ticket-739.

Couverture :
- erreur réseau puis PR non mergée → la phase 2 est relancée, la seconde
  tentative réussie émet un succès et aucun échec ;
- deux erreurs réseau de suite → l'échec est émis, phase 2 appelée deux fois ;
- une exception qui n'est pas réseau n'est pas retentée ;
- la reprise laisse « nouvelle tentative » dans le journal du pipeline ;
- la reprise reste dans le délai de la phase 2.
"""
import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path

import httpx

from tessera.services.livraison.ci_watcher import CIWatcher
from tessera.services.livraison.livraison import Livraison
from tessera.services.noyau.pipeline_events import EventType, OrchestratorEvent

_PLAFOND_S = 5.0


class _Phase2:
    """Phase 2 double: raises each queued error in turn, then merges."""

    def __init__(self, erreurs: list[BaseException]) -> None:
        self.erreurs = erreurs
        self.appels = 0

    async def __call__(self, pr_number: int) -> Livraison:
        self.appels += 1
        if self.erreurs:
            raise self.erreurs.pop(0)
        return Livraison(pr_number=pr_number, merged=True)


def _pr_ouverte() -> Callable[[int], Awaitable[str]]:
    async def lire(pr_number: int) -> str:
        return "open"

    return lire


async def _surveiller(
    phase2: Callable[[int], Awaitable[Livraison]],
    log_path: Path | None = None,
    timeout_phase2_s: float = 1200.0,
) -> tuple[bool, list[OrchestratorEvent]]:
    watcher = CIWatcher(timeout_phase2_s=timeout_phase2_s)
    events: list[OrchestratorEvent] = []

    async def collect(event: OrchestratorEvent) -> None:
        events.append(event)

    await watcher.surveiller(
        "proj", "ticket-001", 8, phase2, collect,
        pipeline_log_path=log_path, etat_pr=_pr_ouverte(),
    )
    merge = await asyncio.wait_for(
        watcher.attendre_merge("proj", "ticket-001"), _PLAFOND_S
    )
    return merge, events


def _done(events: list[OrchestratorEvent]) -> list[OrchestratorEvent]:
    return [e for e in events if e.type is EventType.CI_MERGE_DONE]


async def test_network_error_then_open_pr_replays_phase_2_and_succeeds() -> None:
    phase2 = _Phase2([httpx.RemoteProtocolError("Server disconnected")])

    merge, events = await _surveiller(phase2)

    assert merge is True
    assert phase2.appels == 2
    done = _done(events)
    assert len(done) == 1
    assert done[0].data["merged"] is True
    assert [e for e in events if e.type is EventType.TICKET_STATUS_CHANGED] == []


async def test_two_network_errors_in_a_row_emit_the_failure() -> None:
    phase2 = _Phase2([httpx.ReadTimeout(""), httpx.ReadTimeout("")])

    merge, events = await _surveiller(phase2)

    assert merge is False
    assert phase2.appels == 2
    done = _done(events)
    assert len(done) == 1
    assert done[0].data["merged"] is False
    assert "ReadTimeout" in done[0].data["arret"]


async def test_non_network_exception_is_not_retried() -> None:
    phase2 = _Phase2([RuntimeError("boom"), RuntimeError("boom")])

    merge, events = await _surveiller(phase2)

    assert merge is False
    assert phase2.appels == 1
    assert "RuntimeError: boom" in _done(events)[0].data["arret"]


async def test_replay_leaves_a_line_in_the_pipeline_log(tmp_path: Path) -> None:
    log_path = tmp_path / "memory" / "pipeline-log.md"
    phase2 = _Phase2([httpx.RemoteProtocolError("Server disconnected")])

    await _surveiller(phase2, log_path=log_path)

    contenu = log_path.read_text(encoding="utf-8")
    assert "nouvelle tentative" in contenu
    assert "RemoteProtocolError" in contenu
    assert "PR #8" in contenu


async def test_replay_stays_inside_the_phase_2_bound() -> None:
    """A second attempt that hangs is cut by the original delay, not a new one."""

    class _LenteApresErreur(_Phase2):
        async def __call__(self, pr_number: int) -> Livraison:
            if not self.erreurs:
                await asyncio.sleep(60.0)
            return await super().__call__(pr_number)

    phase2 = _LenteApresErreur([httpx.ReadTimeout("")])

    merge, events = await _surveiller(phase2, timeout_phase2_s=0.3)

    assert merge is False
    assert "délai dépassé" in _done(events)[0].data["arret"]
