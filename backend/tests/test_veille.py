"""Heartbeat gaps and their route — ticket-1046."""
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tessera.main import app
from tessera.services.noyau.database import init_db
from tessera.services.projets import veille

T0 = datetime(2026, 11, 24, 9, 0)


@pytest.fixture
def db(tmp_path: Path) -> Path:
    chemin = tmp_path / "veille.db"
    asyncio.run(init_db(chemin))
    return chemin


def test_eleven_minute_gap_is_an_interruption(db: Path) -> None:
    assert asyncio.run(veille.battre(db, T0)) is None
    fin = T0 + timedelta(minutes=11)
    interruption = asyncio.run(veille.battre(db, fin))
    assert interruption == veille.Interruption(debut=T0, fin=fin)
    assert asyncio.run(veille.lister(db)).interruptions == [interruption]


def test_five_minute_gap_is_not(db: Path) -> None:
    asyncio.run(veille.battre(db, T0))
    assert asyncio.run(veille.battre(db, T0 + timedelta(minutes=5))) is None
    assert asyncio.run(veille.lister(db)).interruptions == []


def test_31st_interruption_drops_the_oldest(db: Path) -> None:
    instant = T0
    asyncio.run(veille.battre(db, instant))
    for _ in range(31):
        instant += timedelta(hours=1)
        asyncio.run(veille.battre(db, instant))
    liste = asyncio.run(veille.lister(db)).interruptions
    assert len(liste) == 30
    assert liste[0].fin == instant
    assert liste[-1].debut == T0 + timedelta(hours=1)


def test_failed_beat_is_logged_not_raised(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    async def casse(*_: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(veille, "battre", casse)
    with caplog.at_level(logging.ERROR, logger=veille._logger.name):
        asyncio.run(veille.battre_sans_lever("inutile.db"))
    assert "veille_battement_echec" in caplog.text


def test_start_and_stop_the_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    battements: list[int] = []

    async def compte(_: object) -> None:
        battements.append(1)

    monkeypatch.setattr(veille, "battre_sans_lever", compte)

    async def scenario() -> None:
        tache = veille.demarrer()
        await asyncio.sleep(0.05)
        await veille.arreter(tache)
        assert tache.done()

    asyncio.run(scenario())
    assert battements


def test_route_lists_latest_first(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from tessera.config import settings

    chemin = tmp_path / "route.db"
    asyncio.run(init_db(chemin))
    for heures in (0, 1, 2):
        asyncio.run(veille.battre(chemin, T0 + timedelta(hours=heures)))
    monkeypatch.setattr(settings, "ide_db_path", chemin)

    async def rien(_: object) -> None:
        return None

    # Le battement du lifespan ajouterait sa propre interruption.
    monkeypatch.setattr(veille, "battre_sans_lever", rien)
    with TestClient(app) as client:
        corps = client.get("/api/v1/rituels/interruptions").json()
    entrees = corps["interruptions"]
    assert len(entrees) == 2
    assert all({"debut", "fin"} <= set(e) for e in entrees)
    assert entrees[0]["fin"] > entrees[1]["fin"]


@pytest.mark.sans_jeton_par_defaut
def test_route_refuses_without_token() -> None:
    with TestClient(app) as client:
        assert client.get("/api/v1/rituels/interruptions").status_code == 401
