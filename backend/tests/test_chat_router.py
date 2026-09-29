"""Endpoints du chat — ticket-048 et ticket-224."""
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


# ------------------------------------------------------------------
# Liste des conversations — ticket-224
# ------------------------------------------------------------------


async def test_projet_sans_message_rend_liste_vide(workspace: Path) -> None:
    resp = TestClient(app).get("/api/v1/projects/ide-core/chat")

    assert resp.status_code == 200
    assert resp.json() == []


async def test_deux_conversations_triees_de_la_plus_recente(workspace: Path) -> None:
    # L'ancienne est insérée en premier : son MAX(ts) sera inférieur.
    await save_chat_message(settings.ide_db_path, "ide-core", "conv-old", "user", "Premier", 0.0)
    await save_chat_message(settings.ide_db_path, "ide-core", "conv-new", "user", "Deuxième", 0.0)

    body = TestClient(app).get("/api/v1/projects/ide-core/chat").json()

    assert len(body) == 2
    assert body[0]["conversation_id"] == "conv-new"
    assert body[1]["conversation_id"] == "conv-old"


async def test_titre_est_le_premier_message_utilisateur_coupe_a_60(workspace: Path) -> None:
    long_message = "A" * 80
    # Un premier message assistant n'est pas un titre : le titre est le premier
    # message dont le rôle est « user ».
    await save_chat_message(settings.ide_db_path, "ide-core", "c1", "assistant", "Bonjour", 0.0)
    await save_chat_message(settings.ide_db_path, "ide-core", "c1", "user", long_message, 0.0)

    body = TestClient(app).get("/api/v1/projects/ide-core/chat").json()

    assert body[0]["title"] == "A" * 60


async def test_route_existante_par_conversation_id_garde_son_comportement(
    workspace: Path,
) -> None:
    await save_chat_message(settings.ide_db_path, "ide-core", "c1", "user", "Salut", 0.0)

    resp = TestClient(app).get("/api/v1/projects/ide-core/chat/c1")

    assert resp.status_code == 200
    body = resp.json()
    assert body["conversation_id"] == "c1"
    assert len(body["messages"]) == 1
    assert body["messages"][0]["content"] == "Salut"
