"""Rules judged against the project's history — tickets 836 to 838 (ADR-078)."""
from datetime import datetime, timedelta, timezone

from tessera.services.anomalies.modeles import Etape
from tessera.services.anomalies.regles_historiques import etape_longue, mediane_si_assez

T0 = datetime(2026, 11, 5, 10, 0, tzinfo=timezone.utc)


def _ouverte(nom: str = "tests") -> Etape:
    return Etape(nom=nom, debut=T0, fin=None, agent=None)


def _apres(secondes: float) -> datetime:
    return T0 + timedelta(seconds=secondes)


def test_mediane_si_assez_9_samples_is_none() -> None:
    assert mediane_si_assez([1.0] * 9) is None


def test_mediane_si_assez_10_samples_returns_median() -> None:
    assert mediane_si_assez([float(i) for i in range(1, 11)]) == 5.5


def test_etape_longue_just_under_three_medians_is_none() -> None:
    assert etape_longue(_ouverte(), _apres(1799), [600.0] * 10, ticket_id="t") is None


def test_etape_longue_just_over_three_medians_reports() -> None:
    a = etape_longue(_ouverte(), _apres(1801), [600.0] * 10, ticket_id="t")
    assert a is not None
    assert (a.regle, a.seuil, a.mesure, a.unite, a.etape) == (
        "etape_longue", 1800.0, 1801.0, "s", "tests",
    )
    assert a.cle == f"etape_longue:tests:{T0.isoformat()}"


def test_etape_longue_floor_300s_under_is_none() -> None:
    assert etape_longue(_ouverte(), _apres(299), [20.0] * 10, ticket_id="t") is None


def test_etape_longue_floor_300s_over_reports() -> None:
    a = etape_longue(_ouverte(), _apres(301), [20.0] * 10, ticket_id="t")
    assert a is not None and a.seuil == 300.0


def test_etape_longue_without_enough_samples_is_none() -> None:
    assert etape_longue(_ouverte(), _apres(99999), [600.0] * 9, ticket_id="t") is None


def test_etape_longue_ignores_a_closed_stage() -> None:
    close = Etape(nom="tests", debut=T0, fin=_apres(10), agent=None)
    assert etape_longue(close, _apres(99999), [600.0] * 10, ticket_id="t") is None
    abandon = Etape(nom="tests", debut=T0, fin=None, agent=None, abandonnee=True)
    assert etape_longue(abandon, _apres(99999), [600.0] * 10, ticket_id="t") is None
