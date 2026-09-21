"""Endpoints du router agents — ticket-053.

Les services étaient testés, l'assemblage ne l'était pas : un test de service
ne voit ni le parsing de la requête, ni le code HTTP, ni le `detail` renvoyé.
C'est pourtant à ce niveau que les pannes atteignent l'utilisateur.
"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.models.agent import AgentResult
from tessera.models.ticket import TicketStatus


@pytest.fixture(autouse=True)
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ws = tmp_path / "workspace"
    project = ws / "mon-projet"
    (project / "memory").mkdir(parents=True)
    (project / "CLAUDE.md").write_text(
        "# mon-projet\n\nProjet de test.\n", encoding="utf-8"
    )
    for status in ("todo", "in-progress", "in-review", "done", "blocked"):
        (project / "tickets" / status).mkdir(parents=True)
    (project / "tickets" / "todo" / "ticket-001.md").write_text(
        "---\n"
        "id: ticket-001\n"
        'title: "Un ticket"\n'
        "type: feat\n"
        "status: todo\n"
        "priority: medium\n"
        "agent: codeur\n"
        "---\n\n"
        "# ticket-001 — Un ticket\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    monkeypatch.setattr(settings, "llm_provider", "agent_sdk")
    monkeypatch.setattr(settings, "github_token", "")
    monkeypatch.setattr(settings, "github_repo", "")
    return ws


def _client() -> TestClient:
    return TestClient(app)


# ------------------------------------------------------------------
# POST /agents/run
# ------------------------------------------------------------------


def test_run_sur_un_ticket_inexistant_renvoie_404_nommant_le_ticket() -> None:
    resp = _client().post(
        "/api/v1/agents/run",
        json={"project_id": "mon-projet", "ticket_id": "ticket-999", "role": "codeur"},
    )

    assert resp.status_code == 404
    assert "ticket-999" in resp.json()["detail"]


def test_run_sur_un_projet_inexistant_renvoie_404() -> None:
    resp = _client().post(
        "/api/v1/agents/run",
        json={"project_id": "jamais-vu", "ticket_id": "ticket-001", "role": "codeur"},
    )

    assert resp.status_code == 404


def test_run_sans_role_est_refuse_par_la_validation() -> None:
    resp = _client().post(
        "/api/v1/agents/run",
        json={"project_id": "mon-projet", "ticket_id": "ticket-001"},
    )

    assert resp.status_code == 422


def test_run_delegue_au_runner_et_renvoie_son_resultat(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class _FakeRunner:
        async def run(self, **kwargs: object) -> AgentResult:
            captured.update(kwargs)
            return AgentResult(
                role="codeur",
                ticket_id="ticket-001",
                content="du code",
                suggested_status=TicketStatus.in_review,
                duration_ms=12,
            )

    monkeypatch.setattr(
        "tessera.routers.agents._make_runner", lambda project_id: _FakeRunner()
    )

    resp = _client().post(
        "/api/v1/agents/run",
        json={"project_id": "mon-projet", "ticket_id": "ticket-001", "role": "codeur"},
    )

    assert resp.status_code == 200
    assert resp.json()["content"] == "du code"
    # Le contexte projet doit bien être transmis — sans lui l'agent travaille
    # à l'aveugle, et rien ne le signalerait.
    assert "mon-projet" in str(captured["project_context"])


# ------------------------------------------------------------------
# github-sync : une configuration absente doit se dire
# ------------------------------------------------------------------


def test_github_sync_sans_configuration_renvoie_400_explicite() -> None:
    resp = _client().post(
        "/api/v1/agents/run",
        json={"project_id": "mon-projet", "ticket_id": "ticket-001", "role": "github-sync"},
    )

    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert "GITHUB_TOKEN" in detail
    assert "GITHUB_REPO" in detail


# ------------------------------------------------------------------
# POST /agents/create-project
# ------------------------------------------------------------------


def test_create_project_traduit_un_conflit_metier_en_409(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _RefusingCreator:
        async def create_project(self, conversation: object) -> object:
            raise ValueError("Un projet 'mon-projet' existe déjà")

    monkeypatch.setattr(
        "tessera.routers.agents._make_project_creator", lambda: _RefusingCreator()
    )

    resp = _client().post(
        "/api/v1/agents/create-project",
        json={"conversation": [{"role": "user", "content": "un projet"}]},
    )

    assert resp.status_code == 409
    assert "existe déjà" in resp.json()["detail"]


def test_create_project_sans_conversation_est_refuse() -> None:
    resp = _client().post("/api/v1/agents/create-project", json={})
    assert resp.status_code == 422


# ------------------------------------------------------------------
# WS /agents/stream
# ------------------------------------------------------------------


def test_stream_sur_un_ticket_inexistant_renvoie_une_erreur_sans_fermer_brutalement() -> None:
    with _client().websocket_connect("/api/v1/agents/stream") as ws:
        ws.send_json(
            {"project_id": "mon-projet", "ticket_id": "ticket-999", "role": "codeur"}
        )
        assert "ticket-999" in ws.receive_json()["error"]


def test_stream_streame_les_tokens_puis_le_resultat(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _StreamingRunner:
        async def run(self, **kwargs: object) -> AgentResult:
            callback = kwargs.get("stream_callback")
            if callback is not None:
                await callback("un ")  # type: ignore[operator]
                await callback("token")  # type: ignore[operator]
            return AgentResult(
                role="codeur",
                ticket_id="ticket-001",
                content="un token",
                suggested_status=TicketStatus.in_review,
                duration_ms=5,
            )

    monkeypatch.setattr(
        "tessera.routers.agents._make_runner", lambda project_id: _StreamingRunner()
    )

    with _client().websocket_connect("/api/v1/agents/stream") as ws:
        ws.send_json(
            {"project_id": "mon-projet", "ticket_id": "ticket-001", "role": "codeur"}
        )
        assert ws.receive_text() == "un "
        assert ws.receive_text() == "token"
        assert ws.receive_json()["content"] == "un token"
