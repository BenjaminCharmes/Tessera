"""The list of the images a run took — ticket-620."""
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.services import captures

URL = "/api/v1/projects/mon-projet/captures"


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    projet = tmp_path / "workspace" / "mon-projet"
    projet.mkdir(parents=True)
    (projet / "CLAUDE.md").write_text("# mon-projet\n", encoding="utf-8")
    monkeypatch.setattr(settings, "ide_workspace_dir", projet.parent)
    monkeypatch.setattr(settings, "ide_state_dir", tmp_path / "etat")
    with TestClient(app) as c:
        yield c


def _poser(ticket: str, *noms: str) -> None:
    dossier = captures.dossier_des_captures("mon-projet", ticket)
    dossier.mkdir(parents=True)
    for nom in noms:
        (dossier / nom).write_bytes(b"png")


def test_the_route_lists_the_images_of_the_run_sorted(client: TestClient) -> None:
    _poser("ticket-620", "accueil-1280-sombre.png", "accueil-390-clair.png", "liste-390-clair.png")

    reponse = client.get(URL, params={"ticket": "ticket-620"})

    assert reponse.status_code == 200
    assert reponse.json() == {
        "captures": ["accueil-1280-sombre.png", "accueil-390-clair.png", "liste-390-clair.png"]
    }


def test_the_route_lists_nothing_for_a_run_without_capture(client: TestClient) -> None:
    reponse = client.get(URL, params={"ticket": "ticket-620"})
    assert reponse.status_code == 200 and reponse.json() == {"captures": []}


def test_the_route_leaves_out_files_that_are_not_captures(client: TestClient) -> None:
    _poser("ticket-620", "accueil-390-clair.png", "notes.txt", "capture.jpg")
    (captures.dossier_des_captures("mon-projet", "ticket-620") / "sous-dossier").mkdir()

    reponse = client.get(URL, params={"ticket": "ticket-620"})

    assert reponse.json() == {"captures": ["accueil-390-clair.png"]}


def test_the_route_keeps_each_ticket_apart(client: TestClient) -> None:
    _poser("ticket-620", "accueil-390-clair.png")
    _poser("ticket-621", "autre-390-clair.png")

    reponse = client.get(URL, params={"ticket": "ticket-621"})

    assert reponse.json() == {"captures": ["autre-390-clair.png"]}


@pytest.mark.parametrize("ticket", ["../..", "ticket-1/../../x", "ticket-", "autre", "..\\.."])
def test_the_route_refuses_a_ticket_that_escapes_the_folder(
    client: TestClient, ticket: str
) -> None:
    assert client.get(URL, params={"ticket": ticket}).status_code == 404


def test_the_route_needs_a_ticket(client: TestClient) -> None:
    assert client.get(URL).status_code == 422


def test_the_route_refuses_an_unknown_project(client: TestClient) -> None:
    reponse = client.get("/api/v1/projects/inconnu/captures", params={"ticket": "ticket-620"})
    assert reponse.status_code == 404


def test_listing_a_missing_folder_gives_an_empty_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "ide_state_dir", tmp_path / "etat")
    assert captures.lister_les_captures("mon-projet", "ticket-1") == []
