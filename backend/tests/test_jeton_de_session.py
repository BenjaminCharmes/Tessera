"""The session token: effective value, lifecycle and refusal — ticket-878."""
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from tessera.config import settings
from tessera.main import app
from tessera.services.noyau import jeton_de_session
from tessera.utils.secrets import SECRETS

pytestmark = pytest.mark.sans_jeton_par_defaut

_OBSERVE = "/api/v1/orchestrator/observe"
_PROJETS = "/api/v1/projects"


def _bearer(jeton: str | None) -> dict[str, str]:
    return {"Authorization": f"Bearer {jeton}"}


def test_empty_static_token_requires_the_session_token_on_http() -> None:
    client = TestClient(app)
    jeton = jeton_de_session.courant()

    assert jeton
    assert client.get(_PROJETS).status_code == 401
    assert client.get(_PROJETS, headers=_bearer("faux")).status_code == 401
    assert client.get(_PROJETS, headers=_bearer(jeton)).status_code == 200


def test_observation_socket_without_token_is_refused() -> None:
    client = TestClient(app)

    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(_OBSERVE):
            pass

    assert exc.value.code == 4401


def test_observation_socket_with_the_query_token_is_accepted() -> None:
    client = TestClient(app)

    with client.websocket_connect(f"{_OBSERVE}?token={jeton_de_session.courant()}") as ws:
        ws.close()


def test_no_token_at_all_refuses_everything_but_health(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(jeton_de_session._ETAT, "genere", "")
    client = TestClient(app)

    assert jeton_de_session.courant() is None
    assert client.get(_PROJETS, headers=_bearer("")).status_code == 401
    assert client.get(_PROJETS, headers={"Authorization": "Bearer "}).status_code == 401
    assert client.get("/health").status_code == 200


def test_static_token_wins_over_the_generated_one(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "static_token", "x")

    assert jeton_de_session.courant() == "x"


@pytest.fixture
def etat(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    dossier = tmp_path / "etat-du-jeton"
    monkeypatch.setattr(settings, "ide_state_dir", dossier)
    yield dossier / jeton_de_session.NOM_DU_FICHIER


def test_a_static_token_is_required_and_no_file_is_written(
    etat: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "static_token", "x")

    with TestClient(app) as client:
        assert client.get(_PROJETS).status_code == 401
        assert client.get(_PROJETS, headers=_bearer("x")).status_code == 200
        assert not etat.exists()
    assert not etat.exists()


def test_a_generated_token_is_written_during_the_lifespan_and_removed_after(etat: Path) -> None:
    with TestClient(app) as client:
        jeton = jeton_de_session.courant()

        assert jeton and len(jeton) >= 32
        assert etat.read_text(encoding="utf-8") == jeton
        assert jeton in SECRETS.valeurs()
        assert client.get(_PROJETS).status_code == 401
        assert client.get(_PROJETS, headers=_bearer(jeton)).status_code == 200
    assert not etat.exists()
    assert jeton_de_session.courant() is None


def test_a_static_token_deletes_the_stale_file_of_a_previous_start(
    etat: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    etat.parent.mkdir(parents=True)
    etat.write_text("perime", encoding="utf-8")
    monkeypatch.setattr(settings, "static_token", "fixe")

    jeton_de_session.demarrer()

    assert not etat.exists()
    assert jeton_de_session.courant() == "fixe"


def test_without_static_token_start_still_writes_the_drawn_token(etat: Path) -> None:
    jeton_de_session.demarrer()
    try:
        assert etat.read_text(encoding="utf-8") == jeton_de_session.courant()
    finally:
        jeton_de_session.arreter()


def test_each_start_draws_a_new_token(etat: Path) -> None:
    jeton_de_session.demarrer()
    premier = jeton_de_session.courant()
    jeton_de_session.arreter()
    jeton_de_session.demarrer()
    second = jeton_de_session.courant()
    jeton_de_session.arreter()

    assert premier and second and premier != second
