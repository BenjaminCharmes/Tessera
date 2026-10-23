"""A deadline that does not depend on the event loop — ticket-571.

`asyncio.wait_for` vit dans la boucle du backend : si un appel synchrone la
bloque, il ne se déclenche pas à l'heure, et la commande de test continue bien
au-delà de `test_timeout_s`. Ce minuteur tourne dans son propre thread et tue
l'arbre de l'étape à l'échéance, boucle libre ou non.
"""
import threading
import time

from tessera.services.groupe_d_etape import GroupeDEtape
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Marge laissée au `wait_for` : quand la boucle est saine, il passe en premier
#: et le minuteur est annulé avant de tirer.
MARGE_S = 1.0


class MinuteurDEtape:
    """Kills a step's tree at its deadline, from a thread, unless cancelled."""

    def __init__(self, groupe: GroupeDEtape, pid: object, delai_s: float) -> None:
        self._groupe = groupe
        self._pid = pid
        self._verrou = threading.Lock()
        self._annule = False
        self._coupee_a: float | None = None
        self._timer = threading.Timer(delai_s + MARGE_S, self._couper)
        self._timer.daemon = True

    @property
    def coupee_a(self) -> float | None:
        """``time.monotonic()`` of the cut, or ``None`` when it did not fire."""
        with self._verrou:
            return self._coupee_a

    def armer(self) -> None:
        """Start the countdown."""
        self._timer.start()

    def annuler(self) -> None:
        """Cancel the countdown; a cut already decided stays decided."""
        with self._verrou:
            self._annule = True
        self._timer.cancel()

    def _couper(self) -> None:
        with self._verrou:
            if self._annule:
                return
            self._coupee_a = time.monotonic()
        try:
            _logger.warning("minuteur_d_etape_declenche", extra={"pid": str(self._pid)})
            self._groupe.terminer_sync(self._pid)
        except Exception as exc:  # noqa: BLE001 — un thread ne doit rien lever
            _logger.warning("minuteur_d_etape_echec", extra={"erreur": str(exc)})
