"""Capturer une app qui exige un jeton — ticket-437.

Le jeton se lit côté serveur dans le `.env` du projet et ne sort que par
l'entrée standard du script. Aucun navigateur ni processus réel : l'exécuteur
et la création de sous-processus sont simulés.
"""
import asyncio
import json
import logging
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.services import captures
from tessera.services.captures_config import ConfigCaptures, load_captures_config
from tessera.services.captures_session import lire_le_jeton

JETON = "s3cr3t-jeton-de-test"
_SESSION = {"chemin": "/api/session", "jeton_env": "ACCESS_TOKEN", "fichier_env": "backend/.env"}


def _declarer(project: Path, session: object = _SESSION) -> None:
    section: dict[str, object] = {
        "url": "http://localhost:5196",
        "ecrans": [{"nom": "accueil", "chemin": "/"}],
    }
    if session is not None:
        section["session"] = session
    project.joinpath("agents.json").write_text(
        json.dumps({"captures": section}), encoding="utf-8"
    )


def _env(project: Path, contenu: str) -> None:
    (project / "backend").mkdir(exist_ok=True)
    (project / "backend" / ".env").write_text(contenu, encoding="utf-8")


@pytest.fixture(autouse=True)
def projet(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ws = tmp_path / "workspace"
    racine = ws / "vigie"
    racine.mkdir(parents=True)
    (racine / "CLAUDE.md").write_text("# vigie\n", encoding="utf-8")
    _declarer(racine)
    _env(racine, f"AUTRE=1\nACCESS_TOKEN={JETON}\n")
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    monkeypatch.setattr(settings, "ide_state_dir", tmp_path / "etat")

    async def _repond(url: str) -> bool:
        return True

    monkeypatch.setattr(captures, "app_repond", _repond)
    return racine


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def recus(monkeypatch: pytest.MonkeyPatch) -> list[str | None]:
    """Retient le jeton reçu par l'exécuteur et écrit les PNG attendus."""
    jetons: list[str | None] = []

    async def _executeur(
        config: ConfigCaptures, sortie: Path, jeton: str | None
    ) -> None:
        jetons.append(jeton)
        for nom in captures.noms_attendus(config):
            (sortie / nom).write_bytes(b"\x89PNG\r\n\x1a\n")

    monkeypatch.setattr(captures, "executeur_playwright", _executeur)
    return jetons


# --------------------------------------------------------------------------
# La clé `session`
# --------------------------------------------------------------------------


def test_reads_the_optional_session_key(projet: Path) -> None:
    config = load_captures_config(projet)

    assert config is not None and config.session is not None
    assert config.session.chemin == "/api/session"
    assert config.session.jeton_env == "ACCESS_TOKEN"
    assert config.session.fichier_env == "backend/.env"


def test_session_env_file_defaults_to_dot_env(projet: Path) -> None:
    _declarer(projet, {"chemin": "/s", "jeton_env": "T"})

    config = load_captures_config(projet)

    assert config is not None and config.session is not None
    assert config.session.fichier_env == ".env"


def test_section_without_session_behaves_as_before(projet: Path) -> None:
    _declarer(projet, None)

    config = load_captures_config(projet)

    assert config is not None
    assert config.session is None


@pytest.mark.parametrize(
    "session",
    [
        "ACCESS_TOKEN",
        {"jeton_env": "ACCESS_TOKEN"},
        {"chemin": "api/session", "jeton_env": "ACCESS_TOKEN"},
        {"chemin": "/api/session", "jeton_env": ""},
        {"chemin": "/api/session", "jeton_env": "T", "fichier_env": 3},
    ],
)
def test_malformed_session_makes_the_section_unusable(
    projet: Path, session: object
) -> None:
    _declarer(projet, session)

    assert load_captures_config(projet) is None


def test_project_without_session_never_needs_a_token(
    client: TestClient, projet: Path, recus: list[str | None]
) -> None:
    _declarer(projet, None)
    (projet / "backend" / ".env").unlink()

    reponse = client.post("/api/v1/projects/vigie/captures")

    assert reponse.status_code == 200
    assert recus == [None]


# --------------------------------------------------------------------------
# La lecture du jeton
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "contenu",
    [
        f"ACCESS_TOKEN={JETON}",
        f'ACCESS_TOKEN="{JETON}"',
        f"ACCESS_TOKEN='{JETON}'",
        f"export ACCESS_TOKEN={JETON}",
        f"# commentaire\n  ACCESS_TOKEN = {JETON}  # fin de ligne",
        f"ACCESS_TOKEN=ancien\nACCESS_TOKEN={JETON}",
    ],
)
def test_token_is_read_from_the_project_env_file(projet: Path, contenu: str) -> None:
    _env(projet, contenu)
    config = load_captures_config(projet)
    assert config is not None and config.session is not None

    assert lire_le_jeton(projet, config.session) == JETON


@pytest.mark.parametrize("contenu", ["", "AUTRE=1", "ACCESS_TOKEN=", "# ACCESS_TOKEN=x"])
def test_absent_or_empty_token_reads_as_none(projet: Path, contenu: str) -> None:
    _env(projet, contenu)
    config = load_captures_config(projet)
    assert config is not None and config.session is not None

    assert lire_le_jeton(projet, config.session) is None


def test_env_file_outside_the_project_is_refused(projet: Path) -> None:
    (projet.parent / "dehors.env").write_text(f"ACCESS_TOKEN={JETON}", encoding="utf-8")
    _declarer(projet, {**_SESSION, "fichier_env": "../dehors.env"})
    config = load_captures_config(projet)
    assert config is not None and config.session is not None

    assert lire_le_jeton(projet, config.session) is None


# --------------------------------------------------------------------------
# La transmission
# --------------------------------------------------------------------------


def test_token_reaches_the_executor_and_is_not_in_the_response(
    client: TestClient, recus: list[str | None], caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.DEBUG):
        reponse = client.post("/api/v1/projects/vigie/captures")

    assert reponse.status_code == 200
    assert recus == [JETON]
    assert JETON not in reponse.text
    assert JETON not in caplog.text


def test_token_goes_on_stdin_never_on_the_command_line(
    projet: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    entrees: list[bytes] = []
    lancements: list[tuple[tuple[str, ...], str]] = []

    class _Processus:
        returncode = 0

        async def communicate(self, entree: bytes) -> tuple[bytes, bytes]:
            entrees.append(entree)
            return b"", b""

    async def _creer(*args: str, **options: object) -> _Processus:
        lancements.append((args, repr(options)))
        return _Processus()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _creer)
    config = load_captures_config(projet)
    assert config is not None

    asyncio.run(captures.executeur_playwright(config, projet.parent, JETON))

    charge = json.loads(entrees[0])
    assert charge["session"] == {"chemin": "/api/session", "jeton": JETON}
    args, options = lancements[0]
    assert JETON not in " ".join(args)
    assert JETON not in options


def test_script_error_never_echoes_the_token(
    projet: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _Processus:
        returncode = 1

        async def communicate(self, entree: bytes) -> tuple[bytes, bytes]:
            return b"", f"refus pour {JETON}".encode()

    async def _creer(*args: str, **options: object) -> _Processus:
        return _Processus()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _creer)
    config = load_captures_config(projet)
    assert config is not None

    with pytest.raises(captures.CapturesEchouees) as erreur:
        asyncio.run(captures.executeur_playwright(config, projet.parent, JETON))

    assert JETON not in str(erreur.value)
    assert "***" in str(erreur.value)


# --------------------------------------------------------------------------
# Jeton absent
# --------------------------------------------------------------------------


@pytest.mark.parametrize("contenu", ["AUTRE=1", "ACCESS_TOKEN="])
def test_missing_token_answers_409_without_capturing(
    client: TestClient, projet: Path, recus: list[str | None], contenu: str
) -> None:
    _env(projet, contenu)

    reponse = client.post("/api/v1/projects/vigie/captures")

    assert reponse.status_code == 409
    detail = reponse.json()["detail"]
    assert "ACCESS_TOKEN" in detail and "backend/.env" in detail
    assert recus == []
    assert not (settings.ide_state_dir / "captures").exists()


def test_missing_env_file_answers_409_without_capturing(
    client: TestClient, projet: Path, recus: list[str | None]
) -> None:
    (projet / "backend" / ".env").unlink()

    reponse = client.post("/api/v1/projects/vigie/captures")

    assert reponse.status_code == 409
    assert recus == []
