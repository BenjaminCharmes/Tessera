"""A worktree project refuses any mode but `single`, ticket or not — ticket-532, ADR-056.

La branche worktree n'était prise que si un `ticket_id` était fourni : une file
ou un run autonome sans `ticket_id` tournait en silence dans le checkout.
"""
import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.models.ticket import TicketStatus
from tessera.services.pipeline_events import PipelineResult
from tessera.services.run_registry import RUN_REGISTRY

_MESSAGE = "un ticket à la fois"


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
def construits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """The workspace, and the projects an orchestrator was built for."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    monkeypatch.setattr(settings, "github_token", "ghp_exemple")
    appels: list[str] = []

    async def _build(project_id: str, *_: object) -> _OrchestrateurImmediat:
        appels.append(project_id)
        return _OrchestrateurImmediat()

    monkeypatch.setattr("tessera.routers.orchestrator._build_orchestrator", _build)
    return appels


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


def _projet(nom: str, config: dict[str, object]) -> None:
    dossier = settings.ide_workspace_dir / nom
    (dossier / "tickets" / "todo").mkdir(parents=True)
    (dossier / "CLAUDE.md").write_text(f"# {nom}\n", encoding="utf-8")
    (dossier / "agents.json").write_text(json.dumps(config), encoding="utf-8")


def _lancer(client: TestClient, nom: str, mode: str) -> tuple[int, str]:
    reponse = client.post(
        "/api/v1/orchestrator/run", json={"project_id": nom, "mode": mode}
    )
    return reponse.status_code, str(reponse.json().get("detail", ""))


_A_WORKTREE = {"artifacts": "tracked", "worktree": {}}


@pytest.mark.parametrize("mode", ["queue", "autonomous"])
def test_worktree_project_refuses_a_run_without_ticket_id(
    client: TestClient, construits: list[str], mode: str
) -> None:
    _projet("demo", _A_WORKTREE)

    statut, detail = _lancer(client, "demo", mode)

    assert statut == 422
    assert _MESSAGE in detail
    assert construits == []
    assert RUN_REGISTRY.projet_occupe("demo") is False


def test_project_without_worktree_key_still_starts_a_queue_without_ticket_id(
    client: TestClient, construits: list[str]
) -> None:
    _projet("demo", {})

    statut, _ = _lancer(client, "demo", "queue")

    assert statut == 202
    assert construits == ["demo"]
