"""CIWatcher relit une tête de PR en retard avant de refuser — ticket-527.

Couverture :
- tête en retard puis à jour à la lecture suivante → le merge passe ;
- tête restée différente jusqu'au bout de la fenêtre → refus, message actuel ;
- tête qui n'est pas un ancêtre du commit poussé → refus sans relecture ;
- ascendance invérifiable (None, exception, pas de vérificateur) → relecture ;
- la fenêtre est bornée par `relectures`, l'intervalle est injectable.
"""
import asyncio

from tessera.services.ci_watcher import CIWatcher, ControleTete, EstAncetre, TetePr
from tessera.services.livraison import Livraison
from tessera.services.pipeline_events import EventType, OrchestratorEvent

_POUSSE = "a" * 40
_ANCIEN = "b" * 40
_INTRUS = "c" * 40


class _Tetes:
    """Fausse lecture : rend les SHA dans l'ordre, puis répète le dernier."""

    def __init__(self, *valeurs: str) -> None:
        self._valeurs = list(valeurs)
        self.lectures = 0

    async def __call__(self, pr_number: int) -> str | None:
        indice = min(self.lectures, len(self._valeurs) - 1)
        self.lectures += 1
        return self._valeurs[indice]


async def _ancetre_vrai(ancetre: str, descendant: str) -> bool | None:
    return True


async def _ancetre_faux(ancetre: str, descendant: str) -> bool | None:
    return False


async def _ancetre_inconnu(ancetre: str, descendant: str) -> bool | None:
    return None


async def _ancetre_en_erreur(ancetre: str, descendant: str) -> bool | None:
    raise RuntimeError("git indisponible")


async def _surveiller(
    tetes: TetePr, est_ancetre: EstAncetre | None, relectures: int = 4
) -> tuple[bool, int, list[OrchestratorEvent]]:
    watcher = CIWatcher()
    appels: list[int] = []
    events: list[OrchestratorEvent] = []

    async def phase2(pr_number: int) -> Livraison:
        appels.append(pr_number)
        return Livraison(pr_number=pr_number, merged=True)

    async def collect(event: OrchestratorEvent) -> None:
        events.append(event)

    controle = ControleTete(
        pushed_sha=_POUSSE,
        lire_tete=tetes,
        est_ancetre=est_ancetre,
        relectures=relectures,
        intervalle_s=0.0,
    )
    await watcher.surveiller(
        "proj", "ticket-001", 7, phase2, collect, controle_tete=controle
    )
    merge = await asyncio.wait_for(watcher.attendre_merge("proj", "ticket-001"), 5.0)
    return merge, len(appels), events


def _arret(events: list[OrchestratorEvent]) -> str:
    done = [e for e in events if e.type is EventType.CI_MERGE_DONE]
    return str(done[0].data["arret"])


async def test_late_head_up_to_date_on_next_read_lets_merge_through() -> None:
    tetes = _Tetes(_ANCIEN, _POUSSE)

    merge, phase2, _ = await _surveiller(tetes, _ancetre_vrai)

    assert merge is True
    assert phase2 == 1
    assert tetes.lectures == 2


async def test_head_still_late_after_window_refuses_with_current_message() -> None:
    tetes = _Tetes(_ANCIEN)

    merge, phase2, events = await _surveiller(tetes, _ancetre_vrai, relectures=4)

    assert merge is False
    assert phase2 == 0
    assert tetes.lectures == 5
    arret = _arret(events)
    assert "n'est plus le commit poussé" in arret
    assert "La PR reste ouverte." in arret


async def test_head_not_an_ancestor_refuses_without_waiting() -> None:
    tetes = _Tetes(_INTRUS, _POUSSE)

    merge, phase2, events = await _surveiller(tetes, _ancetre_faux)

    assert merge is False
    assert phase2 == 0
    assert tetes.lectures == 1
    assert "n'est plus le commit poussé" in _arret(events)


async def test_unverifiable_ancestry_rereads_then_merges_when_head_catches_up() -> None:
    for verificateur in (_ancetre_inconnu, _ancetre_en_erreur, None):
        tetes = _Tetes(_ANCIEN, _ANCIEN, _POUSSE)

        merge, phase2, _ = await _surveiller(tetes, verificateur)

        assert merge is True
        assert phase2 == 1
        assert tetes.lectures == 3


async def test_unverifiable_ancestry_still_refuses_after_window() -> None:
    tetes = _Tetes(_ANCIEN)

    merge, phase2, _ = await _surveiller(tetes, _ancetre_inconnu, relectures=2)

    assert merge is False
    assert phase2 == 0
    assert tetes.lectures == 3


async def test_head_unreadable_during_window_refuses() -> None:
    lectures = 0

    async def lire(pr_number: int) -> str | None:
        nonlocal lectures
        lectures += 1
        if lectures == 1:
            return _ANCIEN
        raise RuntimeError("GitHub injoignable")

    merge, phase2, events = await _surveiller(lire, _ancetre_vrai)

    assert merge is False
    assert phase2 == 0
    assert "illisible" in _arret(events)
