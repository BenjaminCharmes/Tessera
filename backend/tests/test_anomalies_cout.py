"""Cost anomaly rule and its readings — ticket-837 (ADR-078)."""
from pathlib import Path

from tessera.services.supervision.anomalies.lecture_historique import (
    cout_du_ticket,
    couts_passes,
    ligne_ouverte_du_ticket,
)
from tessera.services.supervision.anomalies.regles_historiques import cout_anormal
from tests.anomalies_base import appel_d_agent, base_neuve, ligne_de_run

T = "ticket-001"


def _median(valeur: float) -> list[float]:
    return [valeur] * 10


def test_cout_anormal_just_under_three_medians_is_none() -> None:
    assert cout_anormal(5.99, _median(2.0), ticket_id=T, ligne_id="l1") is None


def test_cout_anormal_just_over_three_medians_reports() -> None:
    a = cout_anormal(6.01, _median(2.0), ticket_id=T, ligne_id="l1")
    assert a is not None
    assert (a.regle, a.cle, a.seuil, a.unite) == ("cout_anormal", "cout_median:l1", 6.0, "usd")
    assert a.mesure == 6.01


def test_cout_anormal_floor_under_is_none() -> None:
    assert cout_anormal(0.49, _median(0.1), ticket_id=T, ligne_id="l1") is None


def test_cout_anormal_floor_over_reports() -> None:
    a = cout_anormal(0.51, _median(0.1), ticket_id=T, ligne_id="l1")
    assert a is not None and a.seuil == 0.5


def test_cout_anormal_without_enough_samples_skips_the_median_rule() -> None:
    assert cout_anormal(99.0, [2.0] * 9, ticket_id=T, ligne_id="l1") is None


def test_cout_anormal_budget_at_79_percent_is_none() -> None:
    assert cout_anormal(
        0.0, [], ticket_id=T, cumul_usd=3.99, budget_usd=5.0, run_id="r1"
    ) is None


def test_cout_anormal_budget_at_80_percent_reports() -> None:
    a = cout_anormal(0.0, [], ticket_id=T, cumul_usd=4.0, budget_usd=5.0, run_id="r1")
    assert a is not None
    assert (a.cle, a.unite, a.mesure, a.seuil) == ("cout_budget:r1", "pourcent", 80.0, 80.0)


def test_cout_anormal_without_a_budget_never_reports_the_budget_rule() -> None:
    assert cout_anormal(0.0, [], ticket_id=T, cumul_usd=999.0, run_id="r1") is None


def test_cout_anormal_reports_the_median_rule_before_the_budget_rule() -> None:
    a = cout_anormal(
        6.01, _median(2.0), ticket_id=T, ligne_id="l1", cumul_usd=4.5, budget_usd=5.0, run_id="r1"
    )
    assert a is not None and a.cle == "cout_median:l1"


async def test_couts_passes_keeps_the_20_most_recent_single_runs_of_the_project(
    tmp_path: Path,
) -> None:
    db = await base_neuve(tmp_path / "t.db")
    for i in range(21):  # coût = i + 1 : le plus ancien (1) sort
        await ligne_de_run(
            db, f"r{i}", started_at=f"2026-11-01T10:{i:02d}:00+00:00",
            finished_at="2026-11-01T12:00:00+00:00",
        )
        await appel_d_agent(db, f"r{i}", float(i + 1))
    await ligne_de_run(db, "env", mode="queue", ticket_id="queue", finished_at="2026-11-01T12:00:00+00:00")
    await appel_d_agent(db, "env", 50.0)
    await ligne_de_run(db, "autre", project_id="x", finished_at="2026-11-01T12:00:00+00:00")
    await appel_d_agent(db, "autre", 60.0)
    await ligne_de_run(db, "ouvert", started_at="2026-11-02T10:00:00+00:00")
    await appel_d_agent(db, "ouvert", 70.0)
    await ligne_de_run(db, "gratuit", started_at="2026-11-03T10:00:00+00:00",
                       finished_at="2026-11-03T12:00:00+00:00")
    await appel_d_agent(db, "gratuit", 0.0)
    couts = await couts_passes(db, "p")
    assert couts == [float(c) for c in range(21, 1, -1)]


async def test_ligne_ouverte_du_ticket_returns_the_unfinished_single_row_only(
    tmp_path: Path,
) -> None:
    db = await base_neuve(tmp_path / "t.db")
    await ligne_de_run(db, "fini", finished_at="2026-11-01T12:00:00+00:00")
    await ligne_de_run(db, "env", mode="queue", ticket_id="queue")
    await ligne_de_run(db, "autre-ticket", ticket_id="ticket-002")
    assert await ligne_ouverte_du_ticket(db, "p", T) is None
    await ligne_de_run(db, "ouvert", started_at="2026-11-02T10:00:00+00:00")
    ligne = await ligne_ouverte_du_ticket(db, "p", T)
    assert ligne is not None and ligne.id == "ouvert" and ligne.ticket_id == T


async def test_cout_du_ticket_sums_the_calls_of_its_row(tmp_path: Path) -> None:
    db = await base_neuve(tmp_path / "t.db")
    await ligne_de_run(db, "r")
    await ligne_de_run(db, "autre")
    await appel_d_agent(db, "r", 0.25)
    await appel_d_agent(db, "r", 0.5)
    await appel_d_agent(db, "autre", 9.0)
    assert await cout_du_ticket(db, "r") == 0.75
    assert await cout_du_ticket(db, "vide") == 0.0
