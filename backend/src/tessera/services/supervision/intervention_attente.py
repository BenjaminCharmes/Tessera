"""Attendre que le projet soit libre avant d'y écrire — ticket-854, ADR-080.

Une intervention du superviseur est un run `supervision` sous le verrou du projet
(ADR-038) : elle ne double ni un run ni une file, et ne fait pas échouer le
ticket suivant d'une file en 409. Elle attend la fermeture de ce qui tient le
projet (`RUN_REGISTRY.sur_fermeture`, comme `signalements_en_attente`), pendant
au plus `delai_max_s`, puis abandonne sans rien écrire.
"""
import asyncio
import time
from weakref import WeakKeyDictionary

from tessera.services.pipeline.run_registry import RunActif, RunAlreadyInProgress, RunRegistry
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Au-delà, l'intervention abandonne : une file de nuit ne la fait pas attendre sans fin.
DELAI_MAX_S = 30 * 60.0


class _Fermetures:
    """The waiters of a registry, woken when a run of their project closes."""

    def __init__(self, registre: RunRegistry) -> None:
        self._attentes: list[tuple[str, asyncio.Event]] = []
        registre.sur_fermeture(self._sur_fermeture)

    def _sur_fermeture(self, project_id: str) -> None:
        for projet, evenement in list(self._attentes):
            if projet == project_id:
                evenement.set()

    async def attendre(self, project_id: str, delai_s: float) -> bool:
        """Wait for a closing on `project_id`; False when `delai_s` ran out first."""
        entree = (project_id, asyncio.Event())
        self._attentes.append(entree)
        try:
            await asyncio.wait_for(entree[1].wait(), max(delai_s, 0.0))
            return True
        except TimeoutError:
            return False
        finally:
            self._attentes.remove(entree)


# Un seul rappel de fermeture par registre : `sur_fermeture` ne se retire pas.
_PAR_REGISTRE: WeakKeyDictionary[RunRegistry, _Fermetures] = WeakKeyDictionary()


def _fermetures(registre: RunRegistry) -> _Fermetures:
    if registre not in _PAR_REGISTRE:
        _PAR_REGISTRE[registre] = _Fermetures(registre)
    return _PAR_REGISTRE[registre]


def _tenu(registre: RunRegistry, project_id: str) -> bool:
    """A run, or a queue between two tickets, holds the project."""
    return registre.projet_occupe(project_id) or registre.projet_tenu_par_file(project_id)


async def prendre_le_projet(
    registre: RunRegistry, project_id: str, mode: str, titre: str, delai_max_s: float = DELAI_MAX_S
) -> RunActif | None:
    """Open the supervision run on `project_id` once nothing holds it; None if the delay runs out.

    The caller closes the run it gets (`registre.fermer`). Nothing is written here.
    """
    fermetures = _fermetures(registre)
    fin = time.monotonic() + delai_max_s
    while True:
        if not _tenu(registre, project_id):
            try:
                return registre.ouvrir(project_id, None, mode=mode, ticket_titre=titre)
            except RunAlreadyInProgress:
                _logger.info("intervention_projet_repris", extra={"project": project_id})
        if not await fermetures.attendre(project_id, fin - time.monotonic()):
            return None
