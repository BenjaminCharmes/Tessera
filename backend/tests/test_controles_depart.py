"""A run is refused upfront, with every gap listed, when it cannot deliver — ticket-477."""
import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.models.ticket import TicketStatus
from tessera.services.controles_depart import manques_avant_depart
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
    monkeypatch.setattr(settings, "github_token", "ghp_exemple")

    async def _build(project_id: str) -> _OrchestrateurImmediat:
        return _OrchestrateurImmediat()

    monkeypatch.setattr("tessera.routers.orchestrator.build_orchestrator", _build)
    return ws


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


def _projet(ws: Path, config: dict[str, object], nom: str = "demo") -> Path:
    dossier = ws / nom
    (dossier / "tickets" / "todo").mkdir(parents=True)
    (dossier / "CLAUDE.md").write_text(f"# {nom}\n", encoding="utf-8")
    (dossier / "agents.json").write_text(json.dumps(config), encoding="utf-8")
    return dossier


def _workflow(dossier: Path) -> None:
    cible = dossier / ".github" / "workflows"
    cible.mkdir(parents=True)
    (cible / "ci.yml").write_text("name: ci\n", encoding="utf-8")


def _lancer(client: TestClient, nom: str, force: bool = False) -> tuple[int, str]:
    reponse = client.post(
        "/api/v1/orchestrator/run",
        json={"project_id": nom, "ticket_id": "ticket-001", "force": force},
    )
    corps = reponse.json()
    return reponse.status_code, str(corps.get("detail", ""))


_MERGE = {"autonomy": "merge", "github_remote": "octo/demo"}


def test_merge_without_workflow_nor_waiver_is_refused(
    workspace: Path, client: TestClient
) -> None:
    _projet(workspace, _MERGE)
    statut, detail = _lancer(client, "demo")
    assert statut == 422
    assert "merge_without_ci" in detail
    assert RUN_REGISTRY.projet_occupe("demo") is False


def test_merge_with_declared_waiver_starts(workspace: Path, client: TestClient) -> None:
    _projet(workspace, {**_MERGE, "merge_without_ci": True})
    assert _lancer(client, "demo")[0] == 202


def test_pr_without_remote_is_refused(workspace: Path, client: TestClient) -> None:
    _projet(workspace, {"autonomy": "pr"})
    statut, detail = _lancer(client, "demo")
    assert statut == 422
    assert "github_remote" in detail


def test_unknown_test_command_segment_is_refused_by_name(
    workspace: Path, client: TestClient
) -> None:
    config = {"pipeline": {"test_command": "commande-bidon-477 && commande-bidon-478"}}
    _projet(workspace, config)
    statut, detail = _lancer(client, "demo")
    assert statut == 422
    assert "commande-bidon-477" in detail and "commande-bidon-478" in detail


def test_every_gap_is_listed_in_one_answer(workspace: Path, client: TestClient) -> None:
    config = {**_MERGE, "pipeline": {"test_command": "commande-bidon-477"}}
    _projet(workspace, config)
    statut, detail = _lancer(client, "demo")
    assert statut == 422
    assert "merge_without_ci" in detail and "commande-bidon-477" in detail


def test_correct_project_starts_as_before(workspace: Path, client: TestClient) -> None:
    dossier = _projet(
        workspace, {**_MERGE, "pipeline": {"test_command": "./lancer-les-tests.sh"}}
    )
    _workflow(dossier)
    (dossier / "lancer-les-tests.sh").write_text("exit 0\n", encoding="utf-8")
    assert _lancer(client, "demo")[0] == 202


def test_commit_project_without_extras_starts(workspace: Path, client: TestClient) -> None:
    _projet(workspace, {})
    assert _lancer(client, "demo")[0] == 202


def test_force_starts_despite_a_gap(workspace: Path, client: TestClient) -> None:
    _projet(workspace, _MERGE)
    assert _lancer(client, "demo")[0] == 422
    assert _lancer(client, "demo", force=True)[0] == 202


def test_workflow_is_read_from_the_ancestor_repository(workspace: Path) -> None:
    depot = workspace / "depot"
    (depot / ".git").mkdir(parents=True)
    _workflow(depot)
    dossier = _projet(depot, {**_MERGE, "git_root": "ancestor"}, nom="sous-projet")
    assert manques_avant_depart(dossier, "ghp_exemple") == []


def test_unreadable_test_command_is_a_gap(workspace: Path) -> None:
    dossier = _projet(workspace, {"pipeline": {"test_command": "pytest || echo ok"}})
    manques = manques_avant_depart(dossier, "")
    assert len(manques) == 1 and "test_command" in manques[0]


def test_unknown_folder_has_no_gap(workspace: Path) -> None:
    assert manques_avant_depart(workspace / "absent", "") == []


def _projet_a_worktree(
    workspace: Path, declaration: dict[str, object], test_command: str
) -> tuple[Path, Path]:
    """A checkout project and its worktree twin, both under a repository root."""
    config = {
        "git_root": "ancestor",
        "artifacts": "tracked",
        "pipeline": {"test_command": test_command},
        "worktree": declaration,
    }
    depot = workspace / "depot"
    (depot / ".git").mkdir(parents=True)
    projet = _projet(depot / "projects", config, nom="p")
    jumeau = workspace / "wt" / "projects" / "p"
    jumeau.mkdir(parents=True)
    (jumeau / "agents.json").write_text(json.dumps(config), encoding="utf-8")
    return projet, workspace / "wt"


def test_unknown_first_word_of_the_effective_command_is_a_gap(workspace: Path) -> None:
    projet, wt = _projet_a_worktree(
        workspace, {"test_command": "outil-introuvable-524 -q"}, "echo ok"
    )

    manques = manques_avant_depart(projet, "ghp_exemple", racine_worktree=wt)

    assert manques == ["commande de test introuvable : `outil-introuvable-524`"]


def test_unknown_word_of_the_unused_command_is_not_a_gap(workspace: Path) -> None:
    projet, wt = _projet_a_worktree(
        workspace, {"test_command": "./outil-524.sh"}, "commande-bidon-524"
    )
    (wt / "projects" / "p" / "outil-524.sh").write_text("exit 0\n", encoding="utf-8")

    assert manques_avant_depart(projet, "ghp_exemple", racine_worktree=wt) == []
    # Sans worktree, c'est la commande du projet qui se vérifie, comme avant.
    sans = manques_avant_depart(projet, "ghp_exemple")
    assert sans == ["commande de test introuvable : `commande-bidon-524`"]


def test_the_first_word_is_resolved_inside_the_worktree_not_the_checkout(
    workspace: Path,
) -> None:
    projet, wt = _projet_a_worktree(workspace, {"test_command": "./outil-524.sh"}, "echo ok")
    (projet / "outil-524.sh").write_text("exit 0\n", encoding="utf-8")

    manques = manques_avant_depart(projet, "ghp_exemple", racine_worktree=wt)

    assert manques == ["commande de test introuvable : `./outil-524.sh`"]


def test_a_placeholder_in_the_first_word_resolves_to_the_worktree(workspace: Path) -> None:
    projet, wt = _projet_a_worktree(
        workspace, {"test_command": "{worktree}/projects/p/outil-524.sh"}, "echo ok"
    )
    (wt / "projects" / "p" / "outil-524.sh").write_text("exit 0\n", encoding="utf-8")

    assert manques_avant_depart(projet, "ghp_exemple", racine_worktree=wt) == []


def test_an_unknown_placeholder_is_a_gap_naming_it(workspace: Path) -> None:
    projet, wt = _projet_a_worktree(workspace, {"test_command": "{depot}/python"}, "echo ok")

    manques = manques_avant_depart(projet, "ghp_exemple", racine_worktree=wt)

    assert len(manques) == 1 and "{depot}" in manques[0]
