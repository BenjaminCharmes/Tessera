"""The supervision recap route is read-only and follows the journal (ticket-860)."""
from datetime import date
from pathlib import Path

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.routers import supervision_recap
from tessera.services.noyau.database import init_db
from tessera.services.supervision.superviseur_decision_blocs import cible_de
from tessera.services.supervision.superviseur_journal import ajouter_ligne

URL = "/api/v1/supervision/recap"
PROJETS = "/api/v1/projects"


@pytest.fixture
async def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    base = tmp_path / "tessera.db"
    await init_db(base)
    workspace = tmp_path / "workspace"
    (workspace / "ide-core" / "memory").mkdir(parents=True)
    (workspace / "ide-core" / "CLAUDE.md").write_text("# ide-core\n", encoding="utf-8")
    monkeypatch.setattr(settings, "ide_db_path", base)
    monkeypatch.setattr(settings, "ide_workspace_dir", workspace)
    return TestClient(app)


def _memoire() -> Path:
    return settings.ide_workspace_dir / "ide-core" / "memory"


def _ajouter(jour: str, action: str, cible: str, resume: str = "ok") -> None:
    ajouter_ligne(
        _memoire(), jour=date.fromisoformat(jour), action=action, cible=cible, sha="", resume=resume
    )


def test_recap_returns_lines_since_the_date_newest_first(client: TestClient) -> None:
    _ajouter("2026-11-01", "a_toi", "regle-0")
    _ajouter("2026-11-03", "a_toi", "regle-1")
    _ajouter("2026-11-05", "a_toi", "regle-2")
    _ajouter("2026-11-05", "resolu", "regle-2")

    with client:
        corps = client.get(URL, params={"depuis": "2026-11-03"}).json()

    assert corps["depuis"] == "2026-11-03"
    assert [(x["jour"], x["action"], x["cible"]) for x in corps["lignes"]] == [
        ("2026-11-05", "resolu", "regle-2"),
        ("2026-11-05", "a_toi", "regle-2"),
        ("2026-11-03", "a_toi", "regle-1"),
    ]


def test_recap_holds_at_most_200_lines_and_a_future_date_gives_none(client: TestClient) -> None:
    for numero in range(supervision_recap.LIGNES_MAX + 5):
        _ajouter("2026-11-02", "a_toi", f"cas-{numero}")

    with client:
        assert len(client.get(URL).json()["lignes"]) == supervision_recap.LIGNES_MAX
        assert client.get(URL, params={"depuis": "2999-01-01"}).json()["lignes"] == []


def test_recap_without_journal_is_empty_not_an_error(client: TestClient) -> None:
    with client:
        reponse = client.get(URL, params={"depuis": "2026-11-01"})

    assert reponse.status_code == 200
    assert reponse.json() == {"depuis": "2026-11-01", "lignes": [], "a_toi": []}


def test_bad_date_is_422(client: TestClient) -> None:
    with client:
        assert client.get(URL, params={"depuis": "hier"}).status_code == 422
        assert client.get(URL, params={"depuis": "2026-13-45"}).status_code == 422


def test_a_toi_count_matches_open_cases(client: TestClient) -> None:
    _ajouter("2026-11-02", "a_toi", "cas-1", "Touche une porte : à toi.")
    _ajouter("2026-11-03", "a_toi", "cas-2", "Tri impossible.")
    _ajouter("2026-11-04", "resolu", "cas-1")

    with client:
        recap = client.get(URL, params={"depuis": "2026-11-04"}).json()
        projets = client.get(PROJETS).json()

    # Un cas ouvert le reste quel que soit `depuis` ; le compte du projet le suit.
    assert recap["a_toi"] == [
        {"jour": "2026-11-03", "cible": "cas-2", "recommandation": "Tri impossible."}
    ]
    assert {p["id"]: p["superviseur_a_toi"] for p in projets} == {"ide-core": 1}


def test_a_toi_count_is_zero_without_a_journal(client: TestClient) -> None:
    with client:
        assert client.get(PROJETS).json()[0]["superviseur_a_toi"] == 0
        (_memoire() / "supervision.md").write_bytes(b"\xff\xfe\x00 pas de l'utf-8")
        assert client.get(PROJETS).json()[0]["superviseur_a_toi"] == 0


def test_recap_drops_a_settled_case_but_keeps_its_line(client: TestClient) -> None:
    bloc = "- **Une règle proposée.** (ADR-1)"
    contraintes = _memoire() / "contraintes.md"
    contraintes.write_text(f"## Proposées\n\n{bloc}\n", encoding="utf-8")
    _ajouter("2026-11-02", "a_toi", cible_de("regle", bloc))
    _ajouter("2026-11-03", "a_toi", "ticket-7")
    with client:
        avant = client.get(URL).json()
        contraintes.write_text(f"## En vigueur\n\n{bloc}\n", encoding="utf-8")
        apres = client.get(URL).json()
        projets = client.get(PROJETS).json()

    assert len(avant["a_toi"]) == 2
    assert [c["cible"] for c in apres["a_toi"]] == ["ticket-7"]
    assert len(apres["lignes"]) == 2
    assert projets[0]["superviseur_a_toi"] == 1


def test_listing_count_ignores_a_case_whose_ticket_is_done(client: TestClient) -> None:
    _ajouter("2026-11-02", "a_toi", "ticket-9")
    with client:
        assert client.get(PROJETS).json()[0]["superviseur_a_toi"] == 1
        fait = settings.ide_workspace_dir / "ide-core" / "tickets" / "done"
        fait.mkdir(parents=True)
        (fait / "ticket-9-un-titre.md").write_text("x", encoding="utf-8")
        assert client.get(PROJETS).json()[0]["superviseur_a_toi"] == 0


def test_recap_has_no_write_method() -> None:
    routes = [r for r in supervision_recap.router.routes if isinstance(r, APIRoute)]
    assert routes
    assert {m for r in routes for m in r.methods} == {"GET"}
