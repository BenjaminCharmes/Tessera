"""`restants` of a live queue counts additions and removals — ticket-560."""
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.services.file_vivante import FileVivante
from tessera.services.run_registry import RUN_REGISTRY, RunActif
from tessera.services.run_status import statut_d_un_run_vivant

_PROJET = "mon-projet"


def _ecrire_ticket(projet: Path, tid: str) -> None:
    (projet / "tickets" / "todo" / f"{tid}.md").write_text(
        f"---\nid: {tid}\ntitle: \"T {tid}\"\ntype: feat\nstatus: todo\n"
        f"priority: medium\nagent: codeur\n---\n\n# {tid}\n",
        encoding="utf-8",
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
def run_vivant() -> Iterator[RunActif]:
    """A queue run handling ticket-001, with ticket-002 behind it."""
    run = RUN_REGISTRY.ouvrir(_PROJET, "ticket-001", mode="queue")
    run.file = FileVivante(["ticket-001", "ticket-002"])
    run.file.marquer_position(1)
    yield run
    RUN_REGISTRY.fermer(run.run_id)


def _restants_api(client: TestClient, run_id: str) -> list[str]:
    resp = client.get(f"/api/v1/runs/{run_id}")
    assert resp.status_code == 200, resp.text
    return list(resp.json()["restants"])


def test_restants_is_the_whole_queue_before_the_first_ticket() -> None:
    file = FileVivante(["ticket-001", "ticket-002", "ticket-003"])

    assert file.restants() == ["ticket-001", "ticket-002", "ticket-003"]


def test_restants_is_what_follows_the_ticket_being_handled() -> None:
    file = FileVivante(["ticket-001", "ticket-002", "ticket-003"])

    file.marquer_position(2)

    assert file.restants() == ["ticket-003"]


def test_restants_is_empty_on_the_last_ticket() -> None:
    file = FileVivante(["ticket-001", "ticket-002"])

    file.marquer_position(2)

    assert file.restants() == []


def test_restants_returns_a_copy() -> None:
    file = FileVivante(["ticket-001", "ticket-002"])

    file.restants().append("ticket-009")

    assert list(file) == ["ticket-001", "ticket-002"]


def test_an_appended_ticket_is_in_restants_without_any_queue_progress(
    client: TestClient, projet: Path, run_vivant: RunActif
) -> None:
    _ecrire_ticket(projet, "ticket-003")

    resp = client.post(
        f"/api/v1/orchestrator/runs/{run_vivant.run_id}/append",
        json={"ticket_ids": ["ticket-003"]},
    )

    assert resp.status_code == 200, resp.text
    assert run_vivant.file_restants == ()
    assert _restants_api(client, run_vivant.run_id) == ["ticket-002", "ticket-003"]


def test_a_removed_ticket_is_no_longer_in_restants(
    client: TestClient, projet: Path, run_vivant: RunActif
) -> None:
    run_vivant.file_restants = ("ticket-002",)

    resp = client.post(
        f"/api/v1/orchestrator/runs/{run_vivant.run_id}/remove",
        json={"ticket_ids": ["ticket-002"]},
    )

    assert resp.status_code == 200, resp.text
    assert resp.json()["retires"] == ["ticket-002"]
    assert _restants_api(client, run_vivant.run_id) == []


def test_a_live_run_without_a_queue_keeps_its_announced_restants() -> None:
    run = RunActif(run_id="r1", project_id=_PROJET, mode="single")
    run.file_restants = ("ticket-005", "ticket-006")

    assert statut_d_un_run_vivant(run).restants == ["ticket-005", "ticket-006"]
    assert run.en_dict()["file_restants"] == ["ticket-005", "ticket-006"]


def test_the_registry_snapshot_carries_the_same_list_as_the_status(
    client: TestClient, projet: Path, run_vivant: RunActif
) -> None:
    assert run_vivant.file is not None
    run_vivant.file.ajouter(["ticket-004"])

    instantane = [r for r in RUN_REGISTRY.instantane() if r["run_id"] == run_vivant.run_id]

    assert len(instantane) == 1
    assert instantane[0]["file_restants"] == ["ticket-002", "ticket-004"]
    assert instantane[0]["file_restants"] == _restants_api(client, run_vivant.run_id)
