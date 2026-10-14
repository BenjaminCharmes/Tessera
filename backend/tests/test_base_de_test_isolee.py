"""The suite never writes into the real database — ticket-422."""
import asyncio
import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.models.ticket import TicketStatus
from tessera.services.database import list_runs
from tessera.services.pipeline_events import PipelineResult


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


def test_db_path_is_under_pytest_temp_dir(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    base = tmp_path_factory.getbasetemp().resolve()
    chemin = settings.ide_db_path.resolve()

    assert base in chemin.parents
    assert chemin != Path("tessera.db").resolve()
    assert chemin.is_file(), "the schema must already be in place"


def test_each_test_gets_its_own_database(_base_de_test_isolee: Path) -> None:
    assert settings.ide_db_path == _base_de_test_isolee


def test_run_started_over_http_is_recorded_in_the_temp_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = tmp_path / "workspace"
    projet = ws / "projet-isole"
    (projet / "tickets" / "todo").mkdir(parents=True)
    (projet / "CLAUDE.md").write_text("# projet-isole\n", encoding="utf-8")
    (projet / "agents.json").write_text(json.dumps({"autonomy": "commit"}), encoding="utf-8")
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)

    async def _build(project_id: str) -> _OrchestrateurImmediat:
        return _OrchestrateurImmediat()

    monkeypatch.setattr("tessera.routers.orchestrator._build_orchestrator", _build)
    base = settings.ide_db_path

    with TestClient(app) as client:
        reponse = client.post(
            "/api/v1/orchestrator/run",
            json={"project_id": "projet-isole", "ticket_id": "ticket-001"},
        )
        assert reponse.status_code == 202
        runs: list[object] = []
        for _ in range(100):
            runs = list(asyncio.run(list_runs(base, "projet-isole")))
            if runs:
                break
            time.sleep(0.05)

    assert len(runs) == 1
