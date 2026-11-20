"""Rituals: file reading, due dates and routes — ticket-902."""
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.main import app
from tessera.services.github import rituels_sync
from tessera.services.projets import rituels as service
from tessera.services.projets.rituels_echeances import Hebdo, Mensuel, Quotidien, Unique, calculer_echeances

MAINTENANT = datetime(2026, 11, 10, 12, 0)
HEBDO = Hebdo(type="hebdo", jour="lundi", heure="18:30")
MENSUEL = Mensuel(type="mensuel", jour=18, heure="10:00", avant=22)

FICHIER = """---
rituels:
  - id: point-revenus
    titre: Point revenus
    rythme: { type: hebdo, jour: lundi, heure: "18:30" }
    duree_min: 30
    phrase: point revenus
    detail: Chiffres.
    projets: [kadoomi]
---
corps
"""


MAL_FORME = """---
rituels:
  - id: a
    rythme: { type: hebdo
---
"""


def test_missing_file_gives_empty_list(tmp_path: Path) -> None:
    assert service.lire_definitions(tmp_path / "absent.md") == ([], None)


def test_unknown_rhythm_type_gives_error(tmp_path: Path) -> None:
    fichier = tmp_path / "rituels.md"
    fichier.write_text(FICHIER.replace("type: hebdo", "type: annuel"), encoding="utf-8")
    definitions, erreur = service.lire_definitions(fichier)
    assert definitions == []
    assert erreur


def test_malformed_yaml_gives_error(tmp_path: Path) -> None:
    fichier = tmp_path / "rituels.md"
    fichier.write_text(MAL_FORME, encoding="utf-8")
    definitions, erreur = service.lire_definitions(fichier)
    assert definitions == []
    assert erreur


def test_valid_file_is_read(tmp_path: Path) -> None:
    fichier = tmp_path / "rituels.md"
    fichier.write_text(FICHIER, encoding="utf-8")
    definitions, erreur = service.lire_definitions(fichier)
    assert erreur is None
    assert definitions[0].id == "point-revenus"


def test_weekly_never_done_is_late() -> None:
    e = calculer_echeances(HEBDO, MAINTENANT, None, None)
    assert e.statut == "en_retard"
    assert e.derniere == datetime(2026, 11, 9, 18, 30)
    assert e.prochaine == datetime(2026, 11, 16, 18, 30)
    assert not e.depasse


def test_weekly_done_after_due_is_done() -> None:
    e = calculer_echeances(HEBDO, MAINTENANT, datetime(2026, 11, 9, 20, 0), None)
    assert e.statut == "fait"


def test_monthly_done_or_late_and_overdue() -> None:
    assert calculer_echeances(MENSUEL, MAINTENANT, None, None).statut == "en_retard"
    fait = calculer_echeances(MENSUEL, MAINTENANT, datetime(2026, 10, 18, 11, 0), None)
    assert fait.statut == "fait"
    tard = calculer_echeances(MENSUEL, datetime(2026, 11, 23), None, None)
    assert tard.derniere == datetime(2026, 11, 18, 10, 0)
    assert tard.depasse
    assert not calculer_echeances(MENSUEL, datetime(2026, 11, 22, 23), None, None).depasse


def test_one_shot_is_upcoming_with_null_last() -> None:
    unique = Unique(type="unique", du="2026-11-23", au="2026-11-27")
    e = calculer_echeances(unique, MAINTENANT, None, None)
    assert (e.statut, e.derniere) == ("a_venir", None)
    assert e.prochaine == datetime(2026, 11, 23)
    assert calculer_echeances(unique, datetime(2026, 11, 28), None, None).depasse


QUOTIDIEN = Quotidien(type="quotidien", heure="18:00")
OUVRES = Quotidien(type="quotidien", heure="18:00", jours="ouvres")


def test_daily_rhythm_is_read(tmp_path: Path) -> None:
    fichier = tmp_path / "rituels.md"
    quotidien = 'rythme: { type: quotidien, heure: "18:00" }'
    texte = FICHIER.replace('rythme: { type: hebdo, jour: lundi, heure: "18:30" }', quotidien)
    fichier.write_text(texte, encoding="utf-8")
    definitions, erreur = service.lire_definitions(fichier)
    assert erreur is None
    assert definitions[0].rythme == QUOTIDIEN


def test_daily_bounds_every_day() -> None:
    matin = calculer_echeances(QUOTIDIEN, datetime(2026, 11, 11, 10, 0), None, None)
    assert matin.derniere == datetime(2026, 11, 10, 18, 0)
    assert matin.prochaine == datetime(2026, 11, 11, 18, 0)
    soir = calculer_echeances(QUOTIDIEN, datetime(2026, 11, 11, 19, 0), None, None)
    assert soir.derniere == datetime(2026, 11, 11, 18, 0)
    assert soir.prochaine == datetime(2026, 11, 12, 18, 0)


def test_daily_bounds_working_days_only() -> None:
    for maintenant in (datetime(2026, 11, 9, 10, 0), datetime(2026, 11, 7, 12, 0)):
        e = calculer_echeances(OUVRES, maintenant, None, None)
        assert e.derniere == datetime(2026, 11, 6, 18, 0)
        assert e.prochaine == datetime(2026, 11, 9, 18, 0)


def test_daily_status_and_never_overdue() -> None:
    maintenant = datetime(2026, 11, 11, 19, 0)
    jamais = calculer_echeances(QUOTIDIEN, maintenant, None, None)
    assert (jamais.statut, jamais.depasse) == ("en_retard", False)
    fait = calculer_echeances(QUOTIDIEN, maintenant, datetime(2026, 11, 11, 18, 30), None)
    assert (fait.statut, fait.depasse) == ("fait", False)
    ancien = calculer_echeances(QUOTIDIEN, datetime(2026, 12, 30, 19, 0), None, None)
    assert not ancien.depasse


def test_postponement_makes_late_upcoming() -> None:
    reporte = MAINTENANT + timedelta(hours=24)
    assert calculer_echeances(HEBDO, MAINTENANT, None, reporte).statut == "a_venir"
    passe = MAINTENANT - timedelta(hours=1)
    assert calculer_echeances(HEBDO, MAINTENANT, None, passe).statut == "en_retard"


def test_routes_done_then_list_and_unknown_404(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fichier = tmp_path / "rituels.md"
    fichier.write_text(FICHIER, encoding="utf-8")
    monkeypatch.setattr(service, "FICHIER", fichier)
    monkeypatch.setattr(rituels_sync, "creer_service", lambda: None)
    rituels_sync.reinitialiser()
    with TestClient(app) as client:
        avant = client.get("/api/v1/rituels").json()
        assert avant["erreur"] is None
        assert avant["rituels"][0]["id"] == "point-revenus"
        assert client.post("/api/v1/rituels/point-revenus/fait").status_code == 204
        apres = client.get("/api/v1/rituels").json()["rituels"][0]
        assert apres["statut"] == "fait"
        assert client.post("/api/v1/rituels/point-revenus/reporter").status_code == 204
        assert client.get("/api/v1/rituels").json()["rituels"][0]["fait_le"]
        assert client.post("/api/v1/rituels/inconnu/fait").status_code == 404
        assert client.post("/api/v1/rituels/inconnu/reporter").status_code == 404
