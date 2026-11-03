"""How an observer's end is logged — ticket-743.

Un onglet qui se ferme laisse un envoi tomber sur une socket close : c'est une
fin normale, pas un avertissement. Les vrais avertissements restent lisibles.
"""
import logging
from typing import Any

import pytest
from websockets.exceptions import ConnectionClosed

from tessera.routers import observation
from tessera.services.event_hub import Abonnement


class _SocketQuiEchoue:
    """A websocket whose every send raises the given error."""

    def __init__(self, erreur: Exception) -> None:
        self._erreur = erreur

    async def accept(self) -> None:
        return None

    async def send_json(self, data: Any) -> None:
        raise self._erreur


@pytest.fixture
def fermetures(monkeypatch: pytest.MonkeyPatch) -> list[Abonnement]:
    """Record every subscription closed by the endpoint."""
    fermes: list[Abonnement] = []
    original = Abonnement.fermer

    def _fermer(self: Abonnement) -> None:
        fermes.append(self)
        original(self)

    monkeypatch.setattr(Abonnement, "fermer", _fermer)
    return fermes


def _erreur_starlette() -> RuntimeError:
    return RuntimeError('Cannot call "send" once a close message has been sent.')


@pytest.mark.parametrize(
    "erreur", [_erreur_starlette(), ConnectionClosed(None, None)]
)
async def test_closed_socket_is_logged_as_info(
    erreur: Exception,
    caplog: pytest.LogCaptureFixture,
    fermetures: list[Abonnement],
) -> None:
    with caplog.at_level(logging.DEBUG, logger=observation.__name__):
        await observation.observe(_SocketQuiEchoue(erreur))  # type: ignore[arg-type]

    ferme = [r for r in caplog.records if r.getMessage() == "observateur_ferme"]
    assert [r.levelno for r in ferme] == [logging.INFO]
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert len(fermetures) == 1


async def test_other_error_is_logged_as_warning_with_its_type(
    caplog: pytest.LogCaptureFixture, fermetures: list[Abonnement]
) -> None:
    with caplog.at_level(logging.DEBUG, logger=observation.__name__):
        await observation.observe(
            _SocketQuiEchoue(ValueError("boom"))  # type: ignore[arg-type]
        )

    avertis = [r for r in caplog.records if r.getMessage() == "observateur_interrompu"]
    assert [r.levelno for r in avertis] == [logging.WARNING]
    assert avertis[0].type_erreur == "ValueError"  # type: ignore[attr-defined]
    assert not [r for r in caplog.records if r.getMessage() == "observateur_ferme"]
    assert len(fermetures) == 1


async def test_unrelated_runtime_error_stays_a_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.DEBUG, logger=observation.__name__):
        await observation.observe(
            _SocketQuiEchoue(RuntimeError("something else"))  # type: ignore[arg-type]
        )

    assert [r.levelno for r in caplog.records] == [logging.WARNING]
