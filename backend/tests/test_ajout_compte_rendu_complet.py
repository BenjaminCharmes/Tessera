"""An append reports every id it was given, and fetches the base once — ticket-658."""
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.routers import orchestrator
from tessera.services.file_vivante import FileVivante, lecteur_sur_la_base, trier_ajouts
from tessera.services.run_registry import RUN_REGISTRY
from tessera.services.ticket_service import TicketService

_PROJET = "mon-projet"


def _contenu(tid: str) -> str:
    return (
        f"---\nid: {tid}\ntitle: \"T {tid}\"\ntype: feat\nstatus: todo\n"
        f"priority: medium\nagent: codeur\n---\n\n# {tid}\n"
    )


@pytest.fixture
def projet(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ws = tmp_path / "workspace"
    chemin = ws / _PROJET
    (chemin / "memory").mkdir(parents=True)
    (chemin / "CLAUDE.md").write_text("# mon-projet\n", encoding="utf-8")
    for statut in ("todo", "in-progress", "in-review", "done", "blocked"):
        (chemin / "tickets" / statut).mkdir(parents=True)
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    return chemin


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def run_file() -> Iterator[tuple[str, FileVivante]]:
    file = FileVivante(["ticket-001"])
    run = RUN_REGISTRY.ouvrir(_PROJET, "ticket-001", mode="queue")
    run.file = file
    yield run.run_id, file
    RUN_REGISTRY.fermer(run.run_id)


def test_every_requested_id_lands_in_exactly_one_list_even_when_added_meanwhile(
    client: TestClient,
    projet: Path,
    run_file: tuple[str, FileVivante],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id, file = run_file
    ids = ["ticket-002", "ticket-003", "ticket-404", "ticket-001"]
    for tid in ("ticket-002", "ticket-003"):
        (projet / "tickets" / "todo" / f"{tid}.md").write_text(_contenu(tid), encoding="utf-8")

    async def trier_puis_concurrent(
        file_: FileVivante, svc: TicketService, demandes: list[str], repli: object = None
    ) -> tuple[list[str], dict[str, str], dict[str, str]]:
        resultat = await trier_ajouts(file_, svc, demandes)
        # Un appel concurrent ajoute ticket-002 entre le tri et l'ajout.
        file_.ajouter(["ticket-002"])
        return resultat

    monkeypatch.setattr(orchestrator, "trier_ajouts", trier_puis_concurrent)

    resp = client.post(
        f"/api/v1/orchestrator/runs/{run_id}/append", json={"ticket_ids": ids}
    )

    assert resp.status_code == 200, resp.text
    corps = resp.json()
    assert corps["ajoutes"] == ["ticket-003"]
    assert corps["ignores"]["ticket-002"] == "déjà dans la file"
    assert corps["ignores"]["ticket-001"] == "déjà dans la file"
    assert list(corps["refuses"]) == ["ticket-404"]
    classes = corps["ajoutes"] + list(corps["ignores"]) + list(corps["refuses"])
    assert sorted(classes) == sorted(ids)
    assert list(file) == ["ticket-001", "ticket-002", "ticket-003"]


class _EspaceDouble:
    """Un espace git qui sert des tickets et compte ses `fetch`."""

    def __init__(self, tickets: dict[str, str]) -> None:
        self.tickets = tickets
        self.fetchs = 0
        self.lectures = 0

    async def lire_ticket_sur_la_base(
        self, ticket_id: str, *, fetch: bool = True
    ) -> tuple[str, str] | None:
        self.lectures += 1
        if fetch:
            self.fetchs += 1
        contenu = self.tickets.get(ticket_id)
        if contenu is None:
            return None
        dossier = "done" if "status: done" in contenu else "todo"
        return f"tickets/{dossier}/{ticket_id}.md", contenu


async def test_appending_several_tickets_absent_from_the_tree_fetches_once(
    projet: Path,
) -> None:
    espace = _EspaceDouble({f"ticket-{n}": _contenu(f"ticket-{n}") for n in (20, 21, 22)})
    repli = lecteur_sur_la_base(espace, _PROJET)
    demandes = ["ticket-20", "ticket-21", "ticket-22", "ticket-99"]

    acceptes, ignores, refuses = await trier_ajouts(
        FileVivante(["ticket-001"]), TicketService(projet, _PROJET), demandes, repli
    )

    assert acceptes == ["ticket-20", "ticket-21", "ticket-22"]
    assert ignores == {}
    assert refuses == {"ticket-99": "ticket introuvable"}
    assert espace.lectures == 4
    assert espace.fetchs == 1


async def test_a_dependency_read_on_the_base_does_not_fetch_again(projet: Path) -> None:
    dependant = _contenu("ticket-30").replace("agent: codeur", "agent: codeur\ndepends_on: [ticket-29]")
    fait = _contenu("ticket-29").replace("status: todo", "status: done")
    espace = _EspaceDouble({"ticket-30": dependant, "ticket-29": fait})
    repli = lecteur_sur_la_base(espace, _PROJET)

    acceptes, _, refuses = await trier_ajouts(
        FileVivante(), TicketService(projet, _PROJET), ["ticket-30"], repli
    )

    assert acceptes == ["ticket-30"]
    assert refuses == {}
    assert espace.lectures == 2
    assert espace.fetchs == 1
