"""The archive stays readable by id and out of the listings — ticket-660."""
import asyncio
from pathlib import Path

import frontmatter  # type: ignore[import-untyped]
import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.services.file_vivante import FileVivante, trier_ajouts
from tessera.services.ticket_archive import hundred_folder, ticket_number
from tessera.services.ticket_service import TicketService
from tests.test_orchestrator import _make_orchestrator

_PROJET = "mon-projet"


def _ecrire(path: Path, ticket_id: str, status: str = "todo", **extra: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    post = frontmatter.Post(
        content="Corps.",
        id=ticket_id,
        title=f"T {ticket_id}",
        type="chore",
        status=status,
        priority="medium",
        agent="codeur",
        **extra,
    )
    path.write_text(frontmatter.dumps(post), encoding="utf-8")


@pytest.fixture
def projet(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ws = tmp_path / "workspace"
    chemin = ws / _PROJET
    (chemin / "memory").mkdir(parents=True)
    (chemin / "CLAUDE.md").write_text("# mon-projet\n", encoding="utf-8")
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    return chemin


def test_hundred_folder_and_number_parsing() -> None:
    assert hundred_folder(612) == "600-699"
    assert hundred_folder(5) == "000-099"
    assert ticket_number(Path("ticket-612-x.md")) == 612
    assert ticket_number(Path("notes.md")) is None


async def test_a_ticket_depending_on_an_archived_one_is_accepted_in_a_queue(
    projet: Path,
) -> None:
    _ecrire(projet / "tickets/archive/done/600-699/ticket-612-old.md", "ticket-612")
    _ecrire(projet / "tickets/todo/ticket-800-next.md", "ticket-800", depends_on=["ticket-612"])

    acceptes, ignores, refuses = await trier_ajouts(
        FileVivante(), TicketService(projet, _PROJET), ["ticket-800"]
    )

    assert acceptes == ["ticket-800"]
    assert ignores == {}
    assert refuses == {}


async def test_an_archived_ticket_is_reported_as_already_done(projet: Path) -> None:
    _ecrire(projet / "tickets/archive/done/600-699/ticket-612-old.md", "ticket-612")

    _, ignores, _ = await trier_ajouts(
        FileVivante(), TicketService(projet, _PROJET), ["ticket-612"]
    )

    assert ignores == {"ticket-612": "déjà terminé"}


async def test_the_next_ticket_may_depend_on_an_archived_one(
    projet: Path, tmp_path: Path
) -> None:
    _ecrire(projet / "tickets/archive/done/600-699/ticket-612-old.md", "ticket-612")
    _ecrire(projet / "tickets/todo/ticket-800-next.md", "ticket-800", depends_on=["ticket-612"])
    orc = _make_orchestrator(tmp_path, ticket_service=TicketService(projet, _PROJET))  # type: ignore[arg-type]

    suivant = await orc.pick_next_ticket(_PROJET)

    assert suivant is not None
    assert suivant.id == "ticket-800"


def test_the_archive_route_files_old_done_tickets(projet: Path) -> None:
    _ecrire(projet / "tickets/done/ticket-612-old.md", "ticket-612", status="done")
    _ecrire(projet / "tickets/todo/ticket-800-top.md", "ticket-800")

    with TestClient(app) as client:
        resp = client.post(f"/api/v1/projects/{_PROJET}/tickets/archive")
        got = client.get(f"/api/v1/projects/{_PROJET}/tickets/ticket-612")

    assert resp.status_code == 200
    assert resp.json() == {"archived": ["ticket-612"]}
    assert (projet / "tickets/archive/done/600-699/ticket-612-old.md").is_file()
    assert got.status_code == 200
    assert got.json()["status"] == "done"
    listed = asyncio.run(TicketService(projet, _PROJET).list_tickets())
    assert [t.id for t in listed] == ["ticket-800"]
