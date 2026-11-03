"""Captures taken by a run live in the ticket's sub-folder — ticket-618."""
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.services import captures


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    projet = tmp_path / "workspace" / "mon-projet"
    projet.mkdir(parents=True)
    (projet / "CLAUDE.md").write_text("# mon-projet\n", encoding="utf-8")
    monkeypatch.setattr(settings, "ide_workspace_dir", projet.parent)
    monkeypatch.setattr(settings, "ide_state_dir", tmp_path / "etat")
    with TestClient(app) as c:
        yield c


def test_the_ticket_folder_sits_under_the_project_folder() -> None:
    base = captures.dossier_des_captures("mon-projet")
    assert captures.dossier_des_captures("mon-projet", "ticket-618") == base / "ticket-618"


@pytest.mark.parametrize("ticket", ["../x", "ticket-1/../../y", "ticket-", "autre"])
def test_a_ticket_id_that_is_not_one_is_refused(ticket: str) -> None:
    with pytest.raises(ValueError):
        captures.dossier_des_captures("mon-projet", ticket)


def test_the_route_serves_the_run_image_from_its_sub_folder(client: TestClient) -> None:
    dossier = captures.dossier_des_captures("mon-projet", "ticket-618")
    dossier.mkdir(parents=True)
    (dossier / "accueil-390-clair.png").write_bytes(b"png-run")

    reponse = client.get(
        "/api/v1/projects/mon-projet/captures/accueil-390-clair.png",
        params={"ticket": "ticket-618"},
    )
    assert reponse.status_code == 200 and reponse.content == b"png-run"
    sans_ticket = client.get("/api/v1/projects/mon-projet/captures/accueil-390-clair.png")
    assert sans_ticket.status_code == 404


def test_the_route_refuses_a_ticket_that_escapes_the_folder(client: TestClient) -> None:
    reponse = client.get(
        "/api/v1/projects/mon-projet/captures/accueil-390-clair.png",
        params={"ticket": "../.."},
    )
    assert reponse.status_code == 404
