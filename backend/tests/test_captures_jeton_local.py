"""Le jeton de session ne part que vers une adresse locale — ticket-753.

Un `agents.json` importé peut déclarer n'importe quelle URL : le jeton lu dans
le `.env` du projet ne doit pas la suivre. L'exécuteur est simulé.
"""
import asyncio
import json
from pathlib import Path

import pytest

from tessera.config import settings
from tessera.services import captures
from tessera.services.captures_config import ConfigCaptures, load_captures_config

JETON = "s3cr3t-jeton-de-test"


def _config(tmp_path: Path, url: str) -> ConfigCaptures:
    section = {
        "url": url,
        "ecrans": [{"nom": "accueil", "chemin": "/"}],
        "session": {"chemin": "/api/session", "jeton_env": "ACCESS_TOKEN"},
    }
    (tmp_path / "agents.json").write_text(json.dumps({"captures": section}), encoding="utf-8")
    config = load_captures_config(tmp_path)
    assert config is not None
    return config


def _capturer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, url: str) -> list[str | None]:
    monkeypatch.setattr(settings, "ide_state_dir", tmp_path / "etat")
    recus: list[str | None] = []

    async def _executeur(config: ConfigCaptures, sortie: Path, jeton: str | None) -> None:
        recus.append(jeton)
        for nom in captures.noms_attendus(config):
            (sortie / nom).write_bytes(b"\x89PNG\r\n\x1a\n")

    asyncio.run(captures.capturer("vigie", _config(tmp_path, url), _executeur, jeton=JETON))
    return recus


def test_session_token_is_withheld_from_a_foreign_host(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _capturer(tmp_path, monkeypatch, "https://exemple.org") == [None]


@pytest.mark.parametrize(
    "url",
    ["http://127.0.0.1:5196", "http://localhost:5196", "http://[::1]:5196"],
)
def test_loopback_url_still_receives_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, url: str
) -> None:
    assert _capturer(tmp_path, monkeypatch, url) == [JETON]


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1.exemple.org",
        "http://localhost.exemple.org",
        "http://127.0.0.1@exemple.com",
        "http://192.168.1.10:5196",
        "http://0.0.0.0:5196",
        "http://",
    ],
)
def test_lookalike_hosts_are_not_local(url: str) -> None:
    assert captures.url_locale(url) is False


def test_payload_omits_the_token_for_a_foreign_host(tmp_path: Path) -> None:
    config = _config(tmp_path, "https://exemple.org")

    charge = json.loads(captures._charge(config, JETON))

    assert "session" not in charge
    assert JETON not in json.dumps(charge)
