"""Chat without tools and closed `agents/run` in an account-agent project — ticket-1051 (ADR-094)."""
import asyncio
import json
from collections.abc import Iterator
from pathlib import Path
from typing import cast

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from tessera.config import settings
from tessera.main import app
from tessera.routers.chat import _CHAT_TOOLS, _build_service
from tessera.services.noyau.database import init_db
from tessera.services.providers.agent_sdk import ClaudeAgentSDKProvider, _build_options

_CHAT_AVEC_SKILLS_ET_WEB: list[dict[str, object]] = [
    {
        "role": "chat", "model": "m", "max_tokens": 100, "prompt_file": "chat.md",
        "skills": ["verifier-mon-travail"], "web": True,
    }
]


def _ecrire(ws: Path, compte: bool, agents: list[dict[str, object]]) -> None:
    projet = ws / "mon-projet"
    for statut in ("todo", "in-progress", "in-review", "done", "blocked"):
        (projet / "tickets" / statut).mkdir(parents=True, exist_ok=True)
    (projet / "memory").mkdir(exist_ok=True)
    (projet / "CLAUDE.md").write_text("# mon-projet\n", encoding="utf-8")
    manifeste: dict[str, object] = {"agents": agents}
    if compte:
        manifeste["worktree"] = {"compte_agent": True}
    (projet / "agents.json").write_text(json.dumps(manifeste), encoding="utf-8")


@pytest.fixture
def ws(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    racine = tmp_path / "ws"
    db = tmp_path / "t.db"
    asyncio.run(init_db(db))
    monkeypatch.setattr(settings, "ide_workspace_dir", racine)
    monkeypatch.setattr(settings, "ide_db_path", db)
    monkeypatch.setattr(settings, "agent_user", "tessera-agent")
    return racine


@pytest.fixture
def client(ws: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    # Le démarrage nettoierait le profil de `tessera-agent` : hors Windows il
    # échoue et laisse `nettoyage_en_echec()` levé pour les tests suivants.
    async def _sans_nettoyage() -> None:
        return None

    monkeypatch.setattr("tessera.main._reinitialiser_le_profil_agent", _sans_nettoyage)
    with TestClient(app) as c:
        yield c


async def test_chat_provider_is_bare_even_with_skills_and_web(ws: Path) -> None:
    _ecrire(ws, True, _CHAT_AVEC_SKILLS_ET_WEB)
    service = await _build_service("mon-projet")
    provider = cast(ClaudeAgentSDKProvider, service._provider)
    assert provider._allowed_tools == []
    assert provider._skills == []
    assert provider._compte_agent is False
    # ADR-093 ne refuse pas cet appel : ni outil, ni skill, ni signaler.
    _build_options(
        system="s", model="m", max_turns=1, max_budget_usd=None, cwd=None,
        allowed_tools=provider._allowed_tools, skills=provider._skills,
        compte_exige=provider._compte_exige,
    )


async def test_chat_service_has_no_git_workspace_without_tools(ws: Path) -> None:
    _ecrire(ws, True, [])
    assert (await _build_service("mon-projet"))._git_workspace is None


async def test_chat_keeps_its_tools_without_account_agent(ws: Path) -> None:
    _ecrire(ws, False, [])
    service = await _build_service("mon-projet")
    assert cast(ClaudeAgentSDKProvider, service._provider)._allowed_tools == _CHAT_TOOLS
    assert service._git_workspace is not None


async def test_chat_keeps_skills_and_web_without_account_agent(ws: Path) -> None:
    _ecrire(ws, False, _CHAT_AVEC_SKILLS_ET_WEB)
    provider = cast(ClaudeAgentSDKProvider, (await _build_service("mon-projet"))._provider)
    assert provider._skills == ["verifier-mon-travail"]
    assert "WebFetch" in provider._allowed_tools


def test_history_reports_sans_outils(client: TestClient, ws: Path) -> None:
    _ecrire(ws, True, [])
    corps = client.get("/api/v1/projects/mon-projet/chat/c1").json()
    assert corps["sans_outils"] is True
    _ecrire(ws, False, [])
    assert client.get("/api/v1/projects/mon-projet/chat/c1").json()["sans_outils"] is False


@pytest.mark.parametrize("role", ["codeur", "reviewer"])
def test_agents_run_and_stream_are_refused_without_a_runner(
    client: TestClient, ws: Path, monkeypatch: pytest.MonkeyPatch, role: str
) -> None:
    _ecrire(ws, True, [])
    appels: list[str] = []
    monkeypatch.setattr("tessera.routers.agents._make_runner", lambda p: appels.append(p))
    corps = {"project_id": "mon-projet", "ticket_id": "ticket-001", "role": role}
    reponse = client.post("/api/v1/agents/run", json=corps)
    assert reponse.status_code == 409, reponse.text
    assert "compte agent" in reponse.json()["detail"]
    with client.websocket_connect("/api/v1/agents/stream") as flux:
        flux.send_json(corps)
        assert "compte agent" in flux.receive_json()["error"]
        with pytest.raises(WebSocketDisconnect) as sortie:
            flux.receive_json()
    assert sortie.value.code == 1008
    assert appels == []


def test_github_sync_still_passes(
    client: TestClient, ws: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _ecrire(ws, True, [])
    monkeypatch.setattr(settings, "github_token", "")
    corps = {"project_id": "mon-projet", "ticket_id": "", "role": "github-sync"}
    # Passé le refus du compte, c'est GITHUB_TOKEN absent qui répond.
    assert client.post("/api/v1/agents/run", json=corps).status_code == 400


def test_agents_run_is_untouched_without_account_agent(client: TestClient, ws: Path) -> None:
    _ecrire(ws, False, [])
    corps = {"project_id": "mon-projet", "ticket_id": "ticket-999", "role": "codeur"}
    assert client.post("/api/v1/agents/run", json=corps).status_code == 404
