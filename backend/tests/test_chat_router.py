"""Endpoints du chat — ticket-048."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.services.database import init_db, save_chat_message


@pytest.fixture
async def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ws = tmp_path / "workspace"
    project = ws / "ide-core"
    (project / "memory").mkdir(parents=True)
    (project / "CLAUDE.md").write_text("# ide-core\n\nProjet test.\n", encoding="utf-8")
    db_path = tmp_path / "tessera.db"
    await init_db(db_path)
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    monkeypatch.setattr(settings, "ide_db_path", db_path)
    return ws


async def test_historique_vide_pour_une_nouvelle_conversation(workspace: Path) -> None:
    resp = TestClient(app).get("/api/v1/projects/ide-core/chat/neuve")

    assert resp.status_code == 200
    body = resp.json()
    assert body["messages"] == []
    assert body["spent_usd"] == 0.0
    assert body["max_usd"] == settings.chat_max_conversation_usd


async def test_historique_restitue_la_conversation_et_son_cout(workspace: Path) -> None:
    # Le critère : la conversation survit à un rechargement de la page.
    await save_chat_message(settings.ide_db_path, "ide-core", "c1", "user", "Salut", 0.0)
    await save_chat_message(settings.ide_db_path, "ide-core", "c1", "assistant", "Bonjour", 0.04)

    body = TestClient(app).get("/api/v1/projects/ide-core/chat/c1").json()

    assert [m["role"] for m in body["messages"]] == ["user", "assistant"]
    assert [m["content"] for m in body["messages"]] == ["Salut", "Bonjour"]
    assert body["spent_usd"] == 0.04


async def test_projet_inconnu_renvoie_404(workspace: Path) -> None:
    resp = TestClient(app).get("/api/v1/projects/inexistant/chat/c1")
    assert resp.status_code == 404
