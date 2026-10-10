"""Keeps the system awake while at least one run is open — ticket-394.

Windows permet à un processus de demander au système de rester éveillé
via `SetThreadExecutionState`. Cela n'empêche pas l'extinction de l'écran
ni une mise en veille forcée (capot fermé, menu Mettre en veille).

Sous tout autre OS, les deux fonctions sont des no-op journalisés une seule
fois, pour ne pas polluer les logs à chaque run.
"""
import platform

from tessera.config import settings
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

# Drapeaux Windows pour SetThreadExecutionState.
_ES_CONTINUOUS: int = 0x80000000
_ES_SYSTEM_REQUIRED: int = 0x00000001

# Évite de répéter le message « non-Windows » à chaque run.
_non_windows_logged: bool = False


def _set_thread_execution_state(drapeaux: int) -> None:
    """Calls SetThreadExecutionState directly — isolated for test mocking.

    `getattr(ctypes, "windll")` contourne la vérification de type statique :
    `ctypes.windll` n'existe pas sur les stubs non-Windows, mais la fonction
    n'est jamais appelée hors Windows (garde dans `retenir`/`relacher`).
    """
    import ctypes

    getattr(ctypes, "windll").kernel32.SetThreadExecutionState(drapeaux)


def retenir() -> None:
    """Ask the OS not to sleep — no-op (logged once) on non-Windows.

    Un échec de l'appel système est journalisé et jamais propagé.
    """
    global _non_windows_logged
    if not settings.keep_awake_during_runs:
        return
    if platform.system() != "Windows":
        if not _non_windows_logged:
            _logger.info("eveil_non_windows", extra={"action": "retenir"})
            _non_windows_logged = True
        return
    try:
        _set_thread_execution_state(_ES_CONTINUOUS | _ES_SYSTEM_REQUIRED)
        _logger.debug("eveil_retenu")
    except Exception as exc:
        _logger.warning("eveil_retenir_erreur", extra={"error": str(exc)})


def relacher() -> None:
    """Release the stay-awake request — no-op (logged once) on non-Windows.

    Un échec de l'appel système est journalisé et jamais propagé.
    """
    global _non_windows_logged
    if not settings.keep_awake_during_runs:
        return
    if platform.system() != "Windows":
        if not _non_windows_logged:
            _logger.info("eveil_non_windows", extra={"action": "relacher"})
            _non_windows_logged = True
        return
    try:
        _set_thread_execution_state(_ES_CONTINUOUS)
        _logger.debug("eveil_relache")
    except Exception as exc:
        _logger.warning("eveil_relacher_erreur", extra={"error": str(exc)})
