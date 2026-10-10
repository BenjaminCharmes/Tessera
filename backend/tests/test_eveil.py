"""Keep-awake integration with RunRegistry — ticket-394.

Chaque test vérifie un critère d'acceptation précis du ticket.
L'appel système réel (SetThreadExecutionState) est systématiquement
remplacé par un mock : les tests sont déterministes sur toute plateforme.
"""
import platform
from unittest.mock import MagicMock

import pytest

from tessera.config import settings
from tessera.services import eveil
from tessera.services.eveil import _ES_CONTINUOUS, _ES_SYSTEM_REQUIRED
from tessera.services.run_registry import RunRegistry


@pytest.fixture(autouse=True)
def reset_non_windows_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remet à zéro le drapeau "déjà loggé" entre chaque test."""
    monkeypatch.setattr(eveil, "_non_windows_logged", False)


@pytest.fixture()
def api_mock(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mock de SetThreadExecutionState, forçant le chemin Windows."""
    mock = MagicMock()
    monkeypatch.setattr(eveil, "_set_thread_execution_state", mock)
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    monkeypatch.setattr(settings, "keep_awake_during_runs", True)
    return mock


# ---------------------------------------------------------------------------
# Critère 1 — premier run → retenir() une seule fois
# ---------------------------------------------------------------------------


def test_premier_run_appelle_retenir_une_fois(
    api_mock: MagicMock,
) -> None:
    """Opening the first run calls retenir() once.

    A second run on a different project must not trigger a second call.
    """
    registry = RunRegistry()

    registry.ouvrir("projet-alpha")
    assert api_mock.call_count == 1
    assert api_mock.call_args[0][0] == _ES_CONTINUOUS | _ES_SYSTEM_REQUIRED

    # Deuxième run (autre projet) : retenir() ne doit pas être rappelé.
    registry.ouvrir("projet-beta")
    assert api_mock.call_count == 1


# ---------------------------------------------------------------------------
# Critère 2 — relacher() seulement à la fermeture du dernier run
# ---------------------------------------------------------------------------


def test_relacher_uniquement_au_dernier_run(
    api_mock: MagicMock,
) -> None:
    """relacher() is called only when the last run closes."""
    registry = RunRegistry()
    run_a = registry.ouvrir("projet-alpha")
    run_b = registry.ouvrir("projet-beta")
    api_mock.reset_mock()

    # Fermeture du premier run : il en reste un, pas de relacher.
    registry.fermer(run_a.run_id)
    relacher_appels = [
        c for c in api_mock.call_args_list if c[0][0] == _ES_CONTINUOUS
    ]
    assert len(relacher_appels) == 0

    # Fermeture du dernier run : relacher() est maintenant appelé.
    registry.fermer(run_b.run_id)
    relacher_appels = [
        c for c in api_mock.call_args_list if c[0][0] == _ES_CONTINUOUS
    ]
    assert len(relacher_appels) == 1


# ---------------------------------------------------------------------------
# Critère 3 — keep_awake_during_runs=False → aucun appel API
# ---------------------------------------------------------------------------


def test_keep_awake_false_aucun_appel_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With keep_awake_during_runs disabled, the system API is never called."""
    api_mock = MagicMock()
    monkeypatch.setattr(eveil, "_set_thread_execution_state", api_mock)
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    monkeypatch.setattr(settings, "keep_awake_during_runs", False)

    registry = RunRegistry()
    run = registry.ouvrir("projet-alpha")
    registry.fermer(run.run_id)

    api_mock.assert_not_called()


# ---------------------------------------------------------------------------
# Critère 4 — exception de l'API système journalisée sans propagation
# ---------------------------------------------------------------------------


def test_exception_api_journalisee_sans_propagation(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A failure from the OS API is logged and never raised."""
    def api_qui_echoue(drapeaux: int) -> None:
        raise OSError("accès refusé par Windows")

    monkeypatch.setattr(eveil, "_set_thread_execution_state", api_qui_echoue)
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    monkeypatch.setattr(settings, "keep_awake_during_runs", True)

    # Aucune des deux fonctions ne doit propager l'exception.
    eveil.retenir()
    eveil.relacher()

    # Le message structuré utilise `extra={"error": ...}` : l'attribut vit
    # sur le LogRecord, pas dans caplog.text qui ne contient que le message.
    erreurs = [getattr(r, "error", None) for r in caplog.records]
    assert "accès refusé par Windows" in erreurs


# ---------------------------------------------------------------------------
# Critère 5 — drapeaux corrects passés à SetThreadExecutionState
# ---------------------------------------------------------------------------


def test_drapeaux_corrects_pour_retenir_et_relacher(
    api_mock: MagicMock,
) -> None:
    """retenir() passes ES_CONTINUOUS|ES_SYSTEM_REQUIRED; relacher() passes ES_CONTINUOUS."""
    eveil.retenir()
    eveil.relacher()

    assert api_mock.call_count == 2
    retenir_drapeau = api_mock.call_args_list[0][0][0]
    relacher_drapeau = api_mock.call_args_list[1][0][0]
    assert retenir_drapeau == _ES_CONTINUOUS | _ES_SYSTEM_REQUIRED
    assert relacher_drapeau == _ES_CONTINUOUS
