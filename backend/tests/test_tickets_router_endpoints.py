"""Endpoints du router tickets — ticket-053."""
import asyncio
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.services.database import init_db
from tessera.services.github_service import PRStatus

_TICKET_MD = """---
id: {id}
title: "{title}"
type: feat
status: todo
priority: medium
agent: codeur
{extra}---

# {id} — {title}
"""


@pytest.fixture(autouse=True)
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ws = tmp_path / "workspace"
    project = ws / "mon-projet"
    (project / "memory").mkdir(parents=True)
    (project / "CLAUDE.md").write_text("# mon-projet\n\nTest.\n", encoding="utf-8")
    for status in ("todo", "in-progress", "in-review", "done", "blocked", "archive"):
        (project / "tickets" / status).mkdir(parents=True)
    (project / "tickets" / "todo" / "ticket-001.md").write_text(
        _TICKET_MD.format(id="ticket-001", title="Un ticket", extra=""),
        encoding="utf-8",
    )
    db_path = tmp_path / "tessera.db"
    asyncio.run(init_db(db_path))
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    monkeypatch.setattr(settings, "ide_db_path", db_path)
    monkeypatch.setattr(settings, "github_token", "")
    return ws


def _client() -> TestClient:
    return TestClient(app)


def _write_ticket(ws: Path, ticket_id: str, *, pr_number: int | None = None) -> None:
    extra = f"pr_number: {pr_number}\n" if pr_number is not None else ""
    (ws / "mon-projet" / "tickets" / "todo" / f"{ticket_id}.md").write_text(
        _TICKET_MD.format(id=ticket_id, title="Avec PR", extra=extra),
        encoding="utf-8",
    )


def _set_github_remote(ws: Path, remote: str) -> None:
    import json

    (ws / "mon-projet" / "agents.json").write_text(
        json.dumps({"github_remote": remote}), encoding="utf-8"
    )


# ------------------------------------------------------------------
# Lecture
# ------------------------------------------------------------------


def test_liste_les_tickets_du_projet() -> None:
    body = _client().get("/api/v1/projects/mon-projet/tickets").json()
    assert [t["id"] for t in body["tickets"]] == ["ticket-001"]
    assert body["unreadable"] == []


def test_liste_filtree_par_statut() -> None:
    body = _client().get("/api/v1/projects/mon-projet/tickets?status=done").json()
    assert body["tickets"] == []


def test_liste_expose_les_tickets_illisibles() -> None:
    """A ticket file without `type` appears in unreadable (ticket-210)."""
    ws_path = settings.ide_workspace_dir
    bad = ws_path / "mon-projet" / "tickets" / "todo" / "ticket-099-bad.md"
    bad.write_text(
        "---\nid: ticket-099\ntitle: Bad\nstatus: todo\npriority: medium\nagent: codeur\n---\n",
        encoding="utf-8",
    )
    body = _client().get("/api/v1/projects/mon-projet/tickets").json()
    assert len(body["unreadable"]) == 1
    assert "ticket-099-bad.md" in body["unreadable"][0]["file_path"]
    assert body["unreadable"][0]["error"]


def test_statut_de_filtre_invalide_est_refuse_lisiblement() -> None:
    # `TicketStatus("n-importe-quoi")` levait un ValueError non capturé :
    # une faute de frappe dans l'URL produisait un 500 opaque (ticket-053).
    resp = _client().get("/api/v1/projects/mon-projet/tickets?status=n-importe-quoi")

    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert "n-importe-quoi" in detail
    assert "todo" in detail  # les valeurs acceptées sont énumérées


def test_ticket_inexistant_renvoie_404_nommant_le_ticket() -> None:
    resp = _client().get("/api/v1/projects/mon-projet/tickets/ticket-999")
    assert resp.status_code == 404
    assert "ticket-999" in resp.json()["detail"]


def test_liste_des_archives() -> None:
    resp = _client().get("/api/v1/projects/mon-projet/tickets/archive")
    assert resp.status_code == 200
    assert resp.json() == []


# ------------------------------------------------------------------
# Création
# ------------------------------------------------------------------


def test_creation_renvoie_201_et_un_id_attribue() -> None:
    resp = _client().post(
        "/api/v1/projects/mon-projet/tickets",
        json={
            "title": "Nouveau ticket",
            "type": "feat",
            "priority": "high",
            "agent": "codeur",
            "description": "Corps du ticket",
        },
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["id"].startswith("ticket-")
    assert body["status"] == "todo"


def test_creation_avec_un_type_hors_enum_est_refusee() -> None:
    resp = _client().post(
        "/api/v1/projects/mon-projet/tickets",
        json={"title": "X", "type": "n-importe-quoi", "priority": "high", "agent": "codeur"},
    )
    assert resp.status_code == 422


def test_creation_accepte_refactor_et_test(workspace: Path) -> None:
    # Ces deux types ont été ajoutés en ticket-050 : le router doit les laisser
    # passer, pas seulement le modèle.
    for ticket_type in ("refactor", "test"):
        resp = _client().post(
            "/api/v1/projects/mon-projet/tickets",
            json={
                "title": f"Un {ticket_type}",
                "type": ticket_type,
                "priority": "low",
                "agent": "codeur",
            },
        )
        assert resp.status_code == 201, ticket_type
        assert resp.json()["type"] == ticket_type


def test_creation_en_lot() -> None:
    resp = _client().post(
        "/api/v1/projects/mon-projet/tickets/batch",
        json={
            "tickets": [
                {
                    "title": "Premier",
                    "type": "feat",
                    "priority": "high",
                    "agent": "codeur",
                    "description": "d1",
                },
                {
                    "title": "Second",
                    "type": "fix",
                    "priority": "low",
                    "agent": "codeur",
                    "description": "d2",
                },
            ]
        },
    )

    assert resp.status_code == 201
    assert len(resp.json()["created"]) == 2


# ------------------------------------------------------------------
# Changement de statut
# ------------------------------------------------------------------


def test_changement_de_statut() -> None:
    resp = _client().patch(
        "/api/v1/projects/mon-projet/tickets/ticket-001",
        json={"status": "in-progress"},
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "in-progress"


def test_changement_de_statut_sur_un_ticket_absent_renvoie_404() -> None:
    resp = _client().patch(
        "/api/v1/projects/mon-projet/tickets/ticket-999",
        json={"status": "done"},
    )
    assert resp.status_code == 404


# ------------------------------------------------------------------
# Pull requests
# ------------------------------------------------------------------


def test_create_pr_sans_github_remote_explique_ce_qui_manque() -> None:
    resp = _client().post(
        "/api/v1/projects/mon-projet/tickets/ticket-001/create-pr",
        json={"head_branch": "ticket-001-slug"},
    )

    assert resp.status_code == 422
    assert "github_remote" in resp.json()["detail"]


def test_create_pr_sans_token_explique_ce_qui_manque(workspace: Path) -> None:
    _set_github_remote(workspace, "owner/repo")

    resp = _client().post(
        "/api/v1/projects/mon-projet/tickets/ticket-001/create-pr",
        json={"head_branch": "ticket-001-slug"},
    )

    assert resp.status_code == 422
    assert "GITHUB_TOKEN" in resp.json()["detail"]


def test_create_pr_refuse_un_doublon_avec_409(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_github_remote(workspace, "owner/repo")
    monkeypatch.setattr(settings, "github_token", "ghp_test")
    _write_ticket(workspace, "ticket-002", pr_number=42)

    resp = _client().post(
        "/api/v1/projects/mon-projet/tickets/ticket-002/create-pr",
        json={"head_branch": "ticket-002-slug"},
    )

    assert resp.status_code == 409
    assert "#42" in resp.json()["detail"]


def test_create_pr_cible_develop_quand_la_base_n_est_pas_precisee(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Le flux du dépôt est ticket -> develop -> main (ticket-049).
    _set_github_remote(workspace, "owner/repo")
    monkeypatch.setattr(settings, "github_token", "ghp_test")
    captured: dict[str, object] = {}

    async def _fake_create(**kwargs: object) -> tuple[int, str]:
        captured.update(kwargs)
        return 7, "https://github.com/owner/repo/pull/7"

    monkeypatch.setattr(
        "tessera.services.github_service.GitHubService.create_pull_request",
        lambda self, **kw: _fake_create(**kw),
    )

    resp = _client().post(
        "/api/v1/projects/mon-projet/tickets/ticket-001/create-pr",
        json={"head_branch": "ticket-001-slug"},
    )

    assert resp.status_code == 201
    assert resp.json()["pr_number"] == 7
    assert captured["base"] is None  # résolu plus bas sur settings.github_base_branch


def test_pr_status_sans_pr_associee_renvoie_404(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_github_remote(workspace, "owner/repo")
    monkeypatch.setattr(settings, "github_token", "ghp_test")

    resp = _client().get("/api/v1/projects/mon-projet/tickets/ticket-001/pr-status")

    assert resp.status_code == 404
    assert "Aucune PR" in resp.json()["detail"]


def test_pr_status_renvoie_l_etat_et_le_statut_ci(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_github_remote(workspace, "owner/repo")
    monkeypatch.setattr(settings, "github_token", "ghp_test")
    _write_ticket(workspace, "ticket-003", pr_number=12)

    async def _fake_status(self: object, pr_number: int) -> PRStatus:
        return PRStatus(
            state="open",
            ci_status="passing",
            pr_url="https://github.com/owner/repo/pull/12",
            pr_number=12,
        )

    monkeypatch.setattr(
        "tessera.services.github_service.GitHubService.get_pull_request_status",
        _fake_status,
    )

    body = _client().get("/api/v1/projects/mon-projet/tickets/ticket-003/pr-status").json()

    assert body["state"] == "open"
    assert body["ci_status"] == "passing"
    assert body["pr_number"] == 12


def test_pr_status_of_a_pr_unknown_to_github_is_404_not_500(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Un pr_number hérité d'un autre dépôt : GitHub répond 404. Remonté en 500,
    # la carte le prenait pour une panne passagère et réessayait sans fin.
    _set_github_remote(workspace, "owner/repo")
    monkeypatch.setattr(settings, "github_token", "ghp_test")
    _write_ticket(workspace, "ticket-003", pr_number=132)

    async def _not_found(self: object, pr_number: int) -> PRStatus:
        request = httpx.Request("GET", f"https://api.github.com/repos/owner/repo/pulls/{pr_number}")
        raise httpx.HTTPStatusError(
            "Not Found", request=request, response=httpx.Response(404, request=request)
        )

    monkeypatch.setattr(
        "tessera.services.github_service.GitHubService.get_pull_request_status",
        _not_found,
    )

    resp = _client().get("/api/v1/projects/mon-projet/tickets/ticket-003/pr-status")

    assert resp.status_code == 404
    assert "#132" in resp.json()["detail"]


def test_le_diff_d_un_ticket_inexistant_renvoie_404(workspace: Path) -> None:
    resp = _client().get("/api/v1/projects/mon-projet/tickets/ticket-404/diff")

    assert resp.status_code == 404


def test_le_diff_d_un_ticket_sans_branche_est_vide(workspace: Path) -> None:
    # Un ticket jamais lance n'a pas de branche : l'ecran doit le dire plutot
    # que d'echouer.
    resp = _client().get("/api/v1/projects/mon-projet/tickets/ticket-001/diff")

    assert resp.status_code == 200
    body = resp.json()
    assert body["branch"] is None
    assert body["diff"] == ""
    assert body["files"] == []
