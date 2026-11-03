"""Capturer les écrans d'un projet lancé — ticket-432.

L'exécuteur (Playwright) et la sonde sont simulés : aucun navigateur n'est
lancé. Ce que ces tests tiennent, c'est le contrat — la section lue, les noms
produits, l'endroit où les images tombent et les refus.
"""
import asyncio
import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.services import captures
from tessera.services.captures_config import (
    ConfigCaptures,
    load_captures_config,
    nom_de_fichier,
)

_CAPTURES = {
    "url": "http://localhost:5196",
    "ecrans": [
        {"nom": "accueil", "chemin": "/"},
        {"nom": "quiz", "chemin": "/#jouer", "clic": "Jouer"},
    ],
}


def _declarer(project: Path, section: object) -> None:
    project.joinpath("agents.json").write_text(
        json.dumps({"project_id": project.name, "captures": section}),
        encoding="utf-8",
    )


@pytest.fixture(autouse=True)
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ws = tmp_path / "workspace"
    for project_id in ("mon-projet", "sans-captures"):
        project = ws / project_id
        project.mkdir(parents=True)
        (project / "CLAUDE.md").write_text(f"# {project_id}\n", encoding="utf-8")
    _declarer(ws / "mon-projet", _CAPTURES)
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    monkeypatch.setattr(settings, "ide_state_dir", tmp_path / "etat")
    return ws


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def app_qui_repond(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _repond(url: str) -> bool:
        return True

    monkeypatch.setattr(captures, "app_repond", _repond)


@pytest.fixture
def executeur_simule(monkeypatch: pytest.MonkeyPatch) -> list[Path]:
    """Écrit un PNG par nom attendu et retient les dossiers de sortie reçus."""
    sorties: list[Path] = []

    async def _executeur(
        config: ConfigCaptures, sortie: Path, jeton: str | None
    ) -> None:
        sorties.append(sortie)
        for nom in captures.noms_attendus(config):
            (sortie / nom).write_bytes(b"\x89PNG\r\n\x1a\n")

    monkeypatch.setattr(captures, "executeur_playwright", _executeur)
    return sorties


# --------------------------------------------------------------------------
# La section `captures`
# --------------------------------------------------------------------------


def test_reads_the_captures_section_of_agents_json(workspace: Path) -> None:
    config = load_captures_config(workspace / "mon-projet")

    assert config is not None
    assert config.url == "http://localhost:5196"
    assert [e.nom for e in config.ecrans] == ["accueil", "quiz"]
    assert config.ecrans[1].chemin == "/#jouer"
    assert config.ecrans[1].clic == "Jouer"
    assert config.ecrans[0].clic == ""


@pytest.mark.parametrize(
    "section",
    [
        None,
        "http://localhost:5196",
        {"url": "localhost:5196", "ecrans": [{"nom": "a", "chemin": "/"}]},
        {"url": "http://localhost:5196", "ecrans": []},
        {"url": "http://localhost:5196", "ecrans": [{"nom": "a", "chemin": "x"}]},
    ],
)
def test_unusable_captures_section_reads_as_none(
    workspace: Path, section: object
) -> None:
    _declarer(workspace / "mon-projet", section)

    assert load_captures_config(workspace / "mon-projet") is None


def test_missing_or_broken_agents_json_reads_as_none(workspace: Path) -> None:
    assert load_captures_config(workspace / "sans-captures") is None
    (workspace / "sans-captures" / "agents.json").write_text("{", encoding="utf-8")
    assert load_captures_config(workspace / "sans-captures") is None


def test_screen_name_is_reduced_to_a_safe_file_name() -> None:
    assert nom_de_fichier("../Écran d'accueil") == "cran-d-accueil"
    assert nom_de_fichier("..") == ""


def test_project_without_captures_answers_409(client: TestClient) -> None:
    reponse = client.post("/api/v1/projects/sans-captures/captures")

    assert reponse.status_code == 409
    assert "captures" in reponse.json()["detail"]


def test_unknown_project_answers_404(client: TestClient) -> None:
    assert client.post("/api/v1/projects/inconnu/captures").status_code == 404


# --------------------------------------------------------------------------
# Les captures
# --------------------------------------------------------------------------


@pytest.mark.usefixtures("app_qui_repond", "executeur_simule")
def test_two_screens_give_eight_named_captures(client: TestClient) -> None:
    reponse = client.post("/api/v1/projects/mon-projet/captures")

    assert reponse.status_code == 200
    noms = reponse.json()["captures"]
    assert len(noms) == 8
    assert set(noms) == {
        f"{ecran}-{largeur}-{theme}.png"
        for ecran in ("accueil", "quiz")
        for largeur in (390, 1440)
        for theme in ("clair", "sombre")
    }


@pytest.mark.usefixtures("app_qui_repond")
def test_images_are_written_outside_the_project_repository(
    client: TestClient, workspace: Path, executeur_simule: list[Path]
) -> None:
    client.post("/api/v1/projects/mon-projet/captures")

    sortie = executeur_simule[0]
    assert sortie == settings.ide_state_dir / "captures" / "mon-projet"
    assert len(list(sortie.glob("*.png"))) == 8
    projet = workspace / "mon-projet"
    assert not sortie.resolve().is_relative_to(projet.resolve())
    assert list(projet.rglob("*.png")) == []


def test_app_that_does_not_answer_gives_409(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _muette(url: str) -> bool:
        return False

    monkeypatch.setattr(captures, "app_repond", _muette)

    reponse = client.post("/api/v1/projects/mon-projet/captures")

    assert reponse.status_code == 409
    assert "http://localhost:5196" in reponse.json()["detail"]
    assert not (settings.ide_state_dir / "captures").exists()


@pytest.mark.usefixtures("app_qui_repond")
def test_failing_executor_answers_502_with_its_message(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _echec(
        config: ConfigCaptures, sortie: Path, jeton: str | None
    ) -> None:
        raise captures.CapturesEchouees("navigateur introuvable")

    monkeypatch.setattr(captures, "executeur_playwright", _echec)

    reponse = client.post("/api/v1/projects/mon-projet/captures")

    assert reponse.status_code == 502
    assert "navigateur introuvable" in reponse.json()["detail"]


@pytest.mark.usefixtures("app_qui_repond")
def test_executor_that_writes_nothing_is_a_failure(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _paresseux(
        config: ConfigCaptures, sortie: Path, jeton: str | None
    ) -> None:
        return None

    monkeypatch.setattr(captures, "executeur_playwright", _paresseux)

    reponse = client.post("/api/v1/projects/mon-projet/captures")

    assert reponse.status_code == 502
    assert "manquantes" in reponse.json()["detail"]


# --------------------------------------------------------------------------
# Servir les images
# --------------------------------------------------------------------------


@pytest.mark.usefixtures("app_qui_repond", "executeur_simule")
def test_serves_a_capture_as_png(client: TestClient) -> None:
    client.post("/api/v1/projects/mon-projet/captures")

    reponse = client.get("/api/v1/projects/mon-projet/captures/accueil-390-clair.png")

    assert reponse.status_code == 200
    assert reponse.headers["content-type"] == "image/png"
    assert reponse.content.startswith(b"\x89PNG")


@pytest.mark.usefixtures("app_qui_repond", "executeur_simule")
@pytest.mark.parametrize(
    "fichier",
    [
        "..%2Fagents.json",
        "..%2F..%2Fsecret.png",
        "inconnu-390-clair.png",
        "accueil-500-clair.png",
        "accueil-390-clair.txt",
    ],
)
def test_refuses_traversal_and_unknown_names(
    client: TestClient, fichier: str
) -> None:
    client.post("/api/v1/projects/mon-projet/captures")

    reponse = client.get(f"/api/v1/projects/mon-projet/captures/{fichier}")

    assert reponse.status_code == 404


# --------------------------------------------------------------------------
# La sonde
# --------------------------------------------------------------------------


def test_probe_sees_a_listening_port_and_a_closed_one() -> None:
    async def _scenario() -> tuple[bool, bool]:
        serveur = await asyncio.start_server(lambda r, w: w.close(), "127.0.0.1", 0)
        port = serveur.sockets[0].getsockname()[1]
        ouvert = await captures.app_repond(f"http://127.0.0.1:{port}")
        serveur.close()
        await serveur.wait_closed()
        ferme = await captures.app_repond(f"http://127.0.0.1:{port}")
        return ouvert, ferme

    assert asyncio.run(_scenario()) == (True, False)
