"""Pending lessons are counted in the project list (ticket-831)."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.services.lecons import nombre_proposees
from tessera.services.database import init_db

BASE = "/api/v1/projects"
DEUX = (
    "# Leçons\n\n## Proposées\n- Quand a, b. (source : ticket-1, 2026-11-05)\n"
    "- Quand c, d. (source : ticket-2, 2026-11-05)\n\n## En vigueur\n- Quand e, f.\n"
)


@pytest.fixture
async def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    base = tmp_path / "tessera.db"
    await init_db(base)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setattr(settings, "ide_db_path", base)
    monkeypatch.setattr(settings, "ide_workspace_dir", workspace)
    return TestClient(app)


def _projet(workspace: Path, nom: str, lecons: str | None) -> None:
    (workspace / nom / "memory").mkdir(parents=True)
    (workspace / nom / "CLAUDE.md").write_text(f"# {nom}\n", encoding="utf-8")
    if lecons is not None:
        (workspace / nom / "memory" / "lecons.md").write_text(lecons, encoding="utf-8")


def test_nombre_proposees_counts_the_lines_under_proposed(tmp_path: Path) -> None:
    (tmp_path / "lecons.md").write_text(DEUX, encoding="utf-8")
    assert nombre_proposees(tmp_path) == 2


def test_nombre_proposees_is_zero_without_a_readable_file(tmp_path: Path) -> None:
    assert nombre_proposees(tmp_path) == 0
    (tmp_path / "lecons.md").write_bytes(b"\xff\xfe\x00 pas de l'utf-8")
    assert nombre_proposees(tmp_path) == 0


def test_project_list_carries_the_pending_lessons_count(client: TestClient) -> None:
    workspace = settings.ide_workspace_dir
    _projet(workspace, "avec", DEUX)
    _projet(workspace, "sans", None)

    with client:
        reponse = client.get(BASE)

    par_id = {p["id"]: p["lecons_proposees"] for p in reponse.json()}
    assert par_id == {"avec": 2, "sans": 0}


def test_the_count_follows_the_file_without_waiting_for_the_project_cache(
    client: TestClient,
) -> None:
    workspace = settings.ide_workspace_dir
    _projet(workspace, "p", None)
    with client:
        assert client.get(BASE).json()[0]["lecons_proposees"] == 0
        (workspace / "p" / "memory" / "lecons.md").write_text(DEUX, encoding="utf-8")
        assert client.get(BASE).json()[0]["lecons_proposees"] == 2
