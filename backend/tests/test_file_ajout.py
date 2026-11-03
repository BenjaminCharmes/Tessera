"""POST /orchestrator/runs/{run_id}/append — ticket-478."""
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.services.file_vivante import FileVivante
from tessera.services.run_registry import RUN_REGISTRY

_PROJET = "mon-projet"


def _ecrire_ticket(
    projet: Path, tid: str, statut: str = "todo", depends_on: list[str] | None = None
) -> None:
    dossier = "done" if statut == "done" else "todo"
    deps = f"depends_on: [{', '.join(depends_on)}]\n" if depends_on else ""
    (projet / "tickets" / dossier / f"{tid}.md").write_text(
        f"---\nid: {tid}\ntitle: \"T {tid}\"\ntype: feat\nstatus: {statut}\n"
        f"priority: medium\nagent: codeur\n{deps}---\n\n# {tid}\n",
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
def run_file() -> Iterator[tuple[str, FileVivante]]:
    """Un run en mode file, déjà ouvert dans le registre, avec ticket-001 en tête."""
    file = FileVivante(["ticket-001"])
    run = RUN_REGISTRY.ouvrir(_PROJET, "ticket-001", mode="queue")
    run.file = file
    yield run.run_id, file
    RUN_REGISTRY.fermer(run.run_id)


def _ajouter(client: TestClient, run_id: str, ids: list[str]):  # type: ignore[no-untyped-def]
    return client.post(
        f"/api/v1/orchestrator/runs/{run_id}/append", json={"ticket_ids": ids}
    )


def test_un_ticket_neuf_est_ajoute_en_fin_de_file(
    client: TestClient, projet: Path, run_file: tuple[str, FileVivante]
) -> None:
    run_id, file = run_file
    _ecrire_ticket(projet, "ticket-002")

    resp = _ajouter(client, run_id, ["ticket-002"])

    assert resp.status_code == 200, resp.text
    assert resp.json()["ajoutes"] == ["ticket-002"]
    assert list(file) == ["ticket-001", "ticket-002"]


def test_un_ticket_deja_dans_la_file_n_est_pas_ajoute_deux_fois(
    client: TestClient, projet: Path, run_file: tuple[str, FileVivante]
) -> None:
    run_id, file = run_file
    _ecrire_ticket(projet, "ticket-001")
    _ecrire_ticket(projet, "ticket-002")

    resp = _ajouter(client, run_id, ["ticket-001", "ticket-002", "ticket-002"])

    corps = resp.json()
    assert corps["ajoutes"] == ["ticket-002"]
    assert set(corps["ignores"]) == {"ticket-001", "ticket-002"}
    assert list(file) == ["ticket-001", "ticket-002"]


def test_un_ticket_deja_fait_n_est_pas_ajoute(
    client: TestClient, projet: Path, run_file: tuple[str, FileVivante]
) -> None:
    run_id, file = run_file
    _ecrire_ticket(projet, "ticket-002", statut="done")

    resp = _ajouter(client, run_id, ["ticket-002"])

    assert resp.json()["ajoutes"] == []
    assert "ticket-002" in resp.json()["ignores"]
    assert list(file) == ["ticket-001"]


def test_un_run_termine_rend_409(client: TestClient, projet: Path) -> None:
    run = RUN_REGISTRY.ouvrir(_PROJET, "ticket-001", mode="queue")
    run.file = FileVivante(["ticket-001"])
    RUN_REGISTRY.fermer(run.run_id)

    assert _ajouter(client, run.run_id, ["ticket-002"]).status_code == 409


def test_un_run_inconnu_rend_409(client: TestClient, projet: Path) -> None:
    assert _ajouter(client, "inconnu", ["ticket-002"]).status_code == 409


def test_une_file_qui_a_fini_de_lire_rend_409(
    client: TestClient, projet: Path, run_file: tuple[str, FileVivante]
) -> None:
    run_id, file = run_file
    file.fermer()

    assert _ajouter(client, run_id, ["ticket-002"]).status_code == 409


def test_un_run_hors_mode_file_rend_409(client: TestClient, projet: Path) -> None:
    run = RUN_REGISTRY.ouvrir(_PROJET, "ticket-001", mode="single")
    try:
        assert _ajouter(client, run.run_id, ["ticket-002"]).status_code == 409
    finally:
        RUN_REGISTRY.fermer(run.run_id)


def test_une_dependance_absente_de_la_file_est_refusee(
    client: TestClient, projet: Path, run_file: tuple[str, FileVivante]
) -> None:
    run_id, file = run_file
    _ecrire_ticket(projet, "ticket-009")
    _ecrire_ticket(projet, "ticket-002", depends_on=["ticket-009"])

    resp = _ajouter(client, run_id, ["ticket-002"])

    assert resp.status_code == 200
    assert resp.json()["ajoutes"] == []
    assert "ticket-009" in resp.json()["refuses"]["ticket-002"]
    assert list(file) == ["ticket-001"]


def test_une_dependance_dans_la_file_ou_deja_faite_est_acceptee(
    client: TestClient, projet: Path, run_file: tuple[str, FileVivante]
) -> None:
    run_id, file = run_file
    _ecrire_ticket(projet, "ticket-008", statut="done")
    _ecrire_ticket(projet, "ticket-001")
    _ecrire_ticket(projet, "ticket-002", depends_on=["ticket-001", "ticket-008"])
    _ecrire_ticket(projet, "ticket-003", depends_on=["ticket-002"])

    resp = _ajouter(client, run_id, ["ticket-002", "ticket-003"])

    assert resp.json()["refuses"] == {}
    assert list(file) == ["ticket-001", "ticket-002", "ticket-003"]


def test_un_ticket_introuvable_est_refuse(
    client: TestClient, projet: Path, run_file: tuple[str, FileVivante]
) -> None:
    run_id, _ = run_file

    resp = _ajouter(client, run_id, ["ticket-404"])

    assert "ticket-404" in resp.json()["refuses"]
