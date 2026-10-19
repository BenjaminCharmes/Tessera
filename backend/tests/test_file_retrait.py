"""Remove a not-yet-started ticket from a live queue — ticket-513."""
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.services.file_vivante import FileFermee, FileVivante
from tessera.services.pipeline_events import PipelineResult
from tessera.services.run_registry import RUN_REGISTRY
from tests.test_file_de_tickets import _events, _OrchestrateurFile

_PROJET = "mon-projet"


def test_retirer_enleve_un_ticket_pas_encore_commence() -> None:
    file = FileVivante(["ticket-001", "ticket-002", "ticket-003"])
    file.marquer_position(1)

    retires, ignores, refuses = file.retirer(["ticket-003"])

    assert retires == ["ticket-003"]
    assert ignores == {} and refuses == {}
    assert list(file) == ["ticket-001", "ticket-002"]


def test_retirer_refuse_le_ticket_en_cours_avec_sa_raison() -> None:
    file = FileVivante(["ticket-001", "ticket-002"])
    file.marquer_position(1)

    retires, _, refuses = file.retirer(["ticket-001"])

    assert retires == []
    assert refuses == {"ticket-001": "en cours : utiliser stop"}
    assert list(file) == ["ticket-001", "ticket-002"]


def test_retirer_refuse_un_ticket_deja_traite() -> None:
    file = FileVivante(["ticket-001", "ticket-002", "ticket-003"])
    file.marquer_position(3)

    retires, _, refuses = file.retirer(["ticket-001"])

    assert retires == []
    assert refuses == {"ticket-001": "déjà traité par la file"}
    assert list(file) == ["ticket-001", "ticket-002", "ticket-003"]


def test_retirer_ignore_un_ticket_absent_et_un_doublon() -> None:
    file = FileVivante(["ticket-001", "ticket-002"])

    retires, ignores, _ = file.retirer(["ticket-002", "ticket-002", "ticket-009"])

    assert retires == ["ticket-002"]
    assert set(ignores) == {"ticket-002", "ticket-009"}


def test_retirer_sur_une_file_fermee_leve() -> None:
    file = FileVivante(["ticket-001"])
    file.fermer()

    with pytest.raises(FileFermee):
        file.retirer(["ticket-001"])


class _OrchestrateurQuiRetire(_OrchestrateurFile):
    """Retire un ticket de la file pendant le premier ticket."""

    def __init__(self, file: FileVivante, retrait: str) -> None:
        super().__init__()
        self._file = file
        self._retrait = retrait
        self.retour: tuple[list[str], dict[str, str], dict[str, str]] | None = None

    async def run_pipeline(self, project_id, ticket_id, on_event, run_id=None,  # type: ignore[no-untyped-def]
                           dialogue=None, envelope_run_id=None) -> PipelineResult:
        if not self.lances:
            self.retour = self._file.retirer([self._retrait, ticket_id])
        return await super().run_pipeline(project_id, ticket_id, on_event)


async def test_apres_un_retrait_la_file_enchaine_sans_le_ticket_retire() -> None:
    file = FileVivante(["ticket-001", "ticket-002", "ticket-003"])
    orch = _OrchestrateurQuiRetire(file, "ticket-002")
    _, on_event = await _events()

    resultats = await orch.run_queue("p", file, on_event)

    assert orch.lances == ["ticket-001", "ticket-003"]
    assert len(resultats) == 2
    assert orch.retour is not None
    # Le ticket en cours, lui, est refusé pendant qu'il tourne.
    assert orch.retour[0] == ["ticket-002"]
    assert "ticket-001" in orch.retour[2]


def _creer_projet(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ws = tmp_path / "workspace"
    chemin = ws / _PROJET
    (chemin / "memory").mkdir(parents=True)
    (chemin / "CLAUDE.md").write_text("# mon-projet\n", encoding="utf-8")
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    return chemin


@pytest.fixture
def projet(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    return _creer_projet(tmp_path, monkeypatch)


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def run_file() -> Iterator[tuple[str, FileVivante]]:
    file = FileVivante(["ticket-001", "ticket-002"])
    run = RUN_REGISTRY.ouvrir(_PROJET, "ticket-001", mode="queue")
    run.file = file
    file.marquer_position(1)
    yield run.run_id, file
    RUN_REGISTRY.fermer(run.run_id)


def _retirer(client: TestClient, run_id: str, ids: list[str]):  # type: ignore[no-untyped-def]
    return client.post(
        f"/api/v1/orchestrator/runs/{run_id}/remove", json={"ticket_ids": ids}
    )


def test_l_api_retire_et_journalise(
    client: TestClient, projet: Path, run_file: tuple[str, FileVivante]
) -> None:
    run_id, file = run_file

    resp = _retirer(client, run_id, ["ticket-002", "ticket-001", "ticket-009"])

    assert resp.status_code == 200, resp.text
    corps = resp.json()
    assert corps["retires"] == ["ticket-002"]
    assert corps["refuses"] == {"ticket-001": "en cours : utiliser stop"}
    assert "ticket-009" in corps["ignores"]
    assert list(file) == ["ticket-001"]
    journal = (projet / "memory" / "pipeline-log.md").read_text(encoding="utf-8")
    assert f"[{_PROJET}] ticket-002 retiré de la file" in journal
    assert "ticket-001 retiré" not in journal


def test_un_run_inconnu_rend_409(client: TestClient, projet: Path) -> None:
    assert _retirer(client, "inconnu", ["ticket-002"]).status_code == 409


def test_un_run_termine_rend_409(client: TestClient, projet: Path) -> None:
    run = RUN_REGISTRY.ouvrir(_PROJET, "ticket-001", mode="queue")
    run.file = FileVivante(["ticket-001", "ticket-002"])
    RUN_REGISTRY.fermer(run.run_id)

    assert _retirer(client, run.run_id, ["ticket-002"]).status_code == 409


def test_une_file_qui_a_fini_de_lire_rend_409(
    client: TestClient, projet: Path, run_file: tuple[str, FileVivante]
) -> None:
    run_id, file = run_file
    file.fermer()

    assert _retirer(client, run_id, ["ticket-002"]).status_code == 409


def test_un_run_hors_mode_file_rend_409(client: TestClient, projet: Path) -> None:
    run = RUN_REGISTRY.ouvrir(_PROJET, "ticket-001", mode="single")
    try:
        assert _retirer(client, run.run_id, ["ticket-002"]).status_code == 409
    finally:
        RUN_REGISTRY.fermer(run.run_id)
