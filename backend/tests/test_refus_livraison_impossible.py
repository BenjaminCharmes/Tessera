"""A run that must deliver is refused upfront when it cannot — ticket-413."""
import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.models.ticket import TicketStatus
from tessera.services.livraison_possible import raison_de_refus_livraison
from tessera.services.pipeline_events import PipelineResult
from tessera.services.run_registry import RUN_REGISTRY


class _OrchestrateurImmediat:
    async def run_pipeline(
        self,
        project_id: str,
        ticket_id: str,
        on_event: object,
        run_id: str | None = None,
        dialogue: object = None,
    ) -> PipelineResult:
        return PipelineResult(
            ticket_id=ticket_id, final_status=TicketStatus.done, rounds=1, approved=True,
        )


@pytest.fixture(autouse=True)
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ws = tmp_path / "workspace"
    ws.mkdir()
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    monkeypatch.setattr(settings, "github_token", "")

    async def _build(project_id: str) -> _OrchestrateurImmediat:
        return _OrchestrateurImmediat()

    monkeypatch.setattr("tessera.routers.orchestrator.build_orchestrator", _build)
    return ws


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


def _projet(ws: Path, autonomy: str, remote: str | None = None) -> str:
    nom = f"projet-{autonomy}"
    dossier = ws / nom
    (dossier / "tickets" / "todo").mkdir(parents=True)
    (dossier / "CLAUDE.md").write_text(f"# {nom}\n", encoding="utf-8")
    config: dict[str, str] = {"autonomy": autonomy}
    if remote:
        config["github_remote"] = remote
    (dossier / "agents.json").write_text(json.dumps(config), encoding="utf-8")
    return nom


def _lancer(client: TestClient, project_id: str) -> int:
    reponse = client.post(
        "/api/v1/orchestrator/run",
        json={"project_id": project_id, "ticket_id": "ticket-001"},
    )
    return reponse.status_code


def test_merge_project_without_remote_is_refused(
    workspace: Path, client: TestClient
) -> None:
    nom = _projet(workspace, "merge")
    reponse = client.post(
        "/api/v1/orchestrator/run", json={"project_id": nom, "ticket_id": "ticket-001"}
    )
    assert reponse.status_code == 422
    assert "github_remote" in reponse.json()["detail"]


def test_pr_project_with_remote_but_no_token_is_refused(
    workspace: Path, client: TestClient
) -> None:
    nom = _projet(workspace, "pr", remote="octo/demo")
    reponse = client.post(
        "/api/v1/orchestrator/run", json={"project_id": nom, "ticket_id": "ticket-001"}
    )
    assert reponse.status_code == 422
    detail = reponse.json()["detail"]
    assert "GITHUB_TOKEN" in detail
    assert "github_remote" not in detail


def test_commit_project_without_remote_starts_normally(
    workspace: Path, client: TestClient
) -> None:
    nom = _projet(workspace, "commit")
    assert _lancer(client, nom) == 202


def test_refused_run_does_not_reserve_the_project(
    workspace: Path, client: TestClient
) -> None:
    nom = _projet(workspace, "merge")
    assert _lancer(client, nom) == 422
    assert RUN_REGISTRY.projet_occupe(nom) is False


def test_second_attempt_after_fix_goes_through(
    workspace: Path, client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    nom = _projet(workspace, "pr")
    assert _lancer(client, nom) == 422
    (workspace / nom / "agents.json").write_text(
        json.dumps({"autonomy": "pr", "github_remote": "octo/demo"}), encoding="utf-8"
    )
    monkeypatch.setattr(settings, "github_token", "ghp_exemple")
    assert _lancer(client, nom) == 202


def test_refusal_reason_names_both_missing_pieces(workspace: Path) -> None:
    nom = _projet(workspace, "merge")
    raison = raison_de_refus_livraison(workspace / nom, "")
    assert raison is not None
    assert "github_remote" in raison and "GITHUB_TOKEN" in raison


def test_refusal_reason_is_none_for_unknown_folder(workspace: Path) -> None:
    assert raison_de_refus_livraison(workspace / "absent", "") is None
