"""Ritual state shared through a GitHub branch — ticket-905."""
import json
from datetime import datetime
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from tessera.main import app
from tessera.services.github import rituels_sync
from tessera.services.github.github_contents import ConflitContenu, FichierDistant
from tessera.services.projets import rituels as service

FICHIER = """---
rituels:
  - id: point-revenus
    titre: Revenue review
    rythme: {type: hebdo, jour: lundi, heure: "18:00"}
    duree_min: 15
    phrase: Look at the numbers.
    detail: Open the page.
---
"""
T1, T2 = datetime(2026, 11, 1, 9), datetime(2026, 11, 8, 9)


class FauxDistant:
    """In-memory stand-in for `GitHubContents`."""

    def __init__(self, contenu: str | None = None, conflits: int = 0) -> None:
        self.contenu = contenu
        self.conflits = conflits
        self.branche_creee = False
        self.lectures = 0
        self.ecritures = 0
        self.apres_conflit: str | None = None

    async def lire_fichier(self, chemin: str, branche: str) -> FichierDistant | None:
        self.lectures += 1
        return None if self.contenu is None else FichierDistant(self.contenu, f"sha{self.lectures}")

    async def ecrire_fichier(
        self, chemin: str, branche: str, contenu: str, message: str, sha: str | None
    ) -> None:
        self.ecritures += 1
        if self.conflits:
            self.conflits -= 1
            self.contenu = self.apres_conflit
            raise ConflitContenu("422")
        self.contenu = contenu

    async def creer_branche(self, branche: str) -> None:
        self.branche_creee = True


class Hors(FauxDistant):
    async def lire_fichier(self, chemin: str, branche: str) -> FichierDistant | None:
        raise httpx.ConnectError("down")


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    fichier = tmp_path / "rituels.md"
    fichier.write_text(FICHIER, encoding="utf-8")
    monkeypatch.setattr(service, "FICHIER", fichier)
    rituels_sync.reinitialiser()
    return TestClient(app)


def _distant(monkeypatch: pytest.MonkeyPatch, faux: FauxDistant | None) -> None:
    monkeypatch.setattr(rituels_sync, "creer_service", lambda: faux)


def test_merge_keeps_latest_and_one_sided_ids() -> None:
    fusion = rituels_sync.fusionner(
        {"a": (T1, None), "seul-local": (T1, T2)},
        {"a": (T2, None), "seul-distant": (None, T1)},
    )

    assert fusion["a"] == (T2, None)
    assert fusion["seul-local"] == (T1, T2)
    assert fusion["seul-distant"] == (None, T1)


def test_done_pushes_only_version_and_rituals(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    faux = FauxDistant()
    _distant(monkeypatch, faux)

    assert client.post("/api/v1/rituels/point-revenus/fait").status_code == 204

    pousse = json.loads(faux.contenu or "")
    assert set(pousse) == {"version", "rituels"}
    assert pousse["rituels"]["point-revenus"]["fait_le"]
    assert set(pousse["rituels"]["point-revenus"]) == {"fait_le", "reporte_jusqua"}
    assert faux.branche_creee


def test_stale_sha_rereads_remerges_and_retries_once(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    faux = FauxDistant(contenu=None, conflits=1)
    faux.apres_conflit = json.dumps(
        {"version": 1, "rituels": {"autre": {"fait_le": T2.isoformat(), "reporte_jusqua": None}}}
    )
    _distant(monkeypatch, faux)

    client.post("/api/v1/rituels/point-revenus/fait")

    assert (faux.lectures, faux.ecritures) == (2, 2)
    final = json.loads(faux.contenu or "")["rituels"]
    assert set(final) == {"autre", "point-revenus"}


@pytest.mark.parametrize("mode", ["sans-jeton", "reseau"])
def test_get_is_local_without_token_or_network(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    _distant(monkeypatch, None if mode == "sans-jeton" else Hors())

    reponse = client.get("/api/v1/rituels")

    assert reponse.status_code == 200
    assert reponse.json()["synchro"] == "locale"


def test_get_pulls_remote_state_and_never_creates_the_branch(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    faux = FauxDistant(
        json.dumps(
            {"version": 1, "rituels": {"point-revenus": {"fait_le": T2.isoformat()}}}
        )
    )
    _distant(monkeypatch, faux)

    corps = client.get("/api/v1/rituels").json()

    assert corps["synchro"] == "github"
    assert corps["rituels"][0]["fait_le"].startswith("2026-11-08")
    assert not faux.branche_creee and faux.ecritures == 0


def test_pull_is_remembered_for_a_minute(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    faux = FauxDistant()
    _distant(monkeypatch, faux)

    client.get("/api/v1/rituels")
    client.get("/api/v1/rituels")

    assert faux.lectures == 1


def test_create_service_needs_token_and_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    from tessera.config import settings

    monkeypatch.setattr(settings, "github_token", "")
    assert rituels_sync.creer_service() is None
    monkeypatch.setattr(settings, "github_token", "t")
    monkeypatch.setattr(settings, "github_repo", "o/r")
    assert rituels_sync.creer_service() is not None
