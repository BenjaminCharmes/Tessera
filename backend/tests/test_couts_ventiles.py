"""Ventilation des couts par agent et par modele — ticket-077."""
from pathlib import Path

import pytest

from tessera.services.database import (
    create_run,
    get_usage_breakdown,
    init_db,
    save_agent_call,
)


@pytest.fixture
async def base(tmp_path: Path) -> Path:
    chemin = tmp_path / "tessera.db"
    await init_db(chemin)
    run = await create_run(chemin, "projet-a", "ticket-001")
    await save_agent_call(
        chemin, run, "ticket-001", "codeur", "sonnet",
        input_tokens=1000, output_tokens=500, cache_read_tokens=0,
        cost_usd=0.60, duration_ms=1000,
    )
    await save_agent_call(
        chemin, run, "ticket-001", "codeur", "sonnet",
        input_tokens=500, output_tokens=200, cache_read_tokens=0,
        cost_usd=0.30, duration_ms=800,
    )
    await save_agent_call(
        chemin, run, "ticket-001", "reviewer", "haiku",
        input_tokens=200, output_tokens=100, cache_read_tokens=0,
        cost_usd=0.10, duration_ms=400,
    )
    autre = await create_run(chemin, "projet-b", "ticket-009")
    await save_agent_call(
        chemin, autre, "ticket-009", "codeur", "sonnet",
        input_tokens=100, output_tokens=50, cache_read_tokens=0,
        cost_usd=0.05, duration_ms=200,
    )
    return chemin


async def test_la_ventilation_par_agent_dit_qui_consomme(base: Path) -> None:
    # C'est la granularite la plus actionnable : elle dit si le codeur mange
    # 70 % du budget, ou si le reviewer coute plus cher que prevu parce qu'il
    # relit tout le diff a chaque tour.
    ventilation = await get_usage_breakdown(base, "projet-a")

    par_agent = {a["role"]: a for a in ventilation["per_agent"]}
    assert par_agent["codeur"]["total_cost_usd"] == pytest.approx(0.90)
    assert par_agent["codeur"]["call_count"] == 2
    assert par_agent["reviewer"]["total_cost_usd"] == pytest.approx(0.10)


async def test_le_plus_couteux_vient_en_premier(base: Path) -> None:
    ventilation = await get_usage_breakdown(base, "projet-a")

    assert [a["role"] for a in ventilation["per_agent"]] == ["codeur", "reviewer"]


async def test_la_ventilation_par_modele_prepare_les_arbitrages(base: Path) -> None:
    ventilation = await get_usage_breakdown(base, "projet-a")

    par_modele = {m["model"]: m["total_cost_usd"] for m in ventilation["per_model"]}
    assert par_modele["sonnet"] == pytest.approx(0.90)
    assert par_modele["haiku"] == pytest.approx(0.10)


async def test_un_projet_ne_voit_que_ses_propres_appels(base: Path) -> None:
    ventilation = await get_usage_breakdown(base, "projet-a")

    assert sum(a["total_cost_usd"] for a in ventilation["per_agent"]) == pytest.approx(1.0)


async def test_sans_projet_la_ventilation_couvre_tout(base: Path) -> None:
    # « Combien me coute Tessera ce mois-ci » n'avait aucune reponse : chaque
    # endpoint etait borne a un projet.
    ventilation = await get_usage_breakdown(base, None)

    par_agent = {a["role"]: a["total_cost_usd"] for a in ventilation["per_agent"]}
    assert par_agent["codeur"] == pytest.approx(0.95)
    assert ventilation["total_cost_usd"] == pytest.approx(1.05)


async def test_la_ventilation_globale_dit_aussi_par_projet(base: Path) -> None:
    # « Combien me coute Tessera, et sur quel projet » n'avait aucune reponse :
    # chaque endpoint etait borne a un projet (ticket-082).
    ventilation = await get_usage_breakdown(base, None)

    par_projet = {p["project_id"]: p["total_cost_usd"] for p in ventilation["per_project"]}
    assert par_projet["projet-a"] == pytest.approx(1.0)
    assert par_projet["projet-b"] == pytest.approx(0.05)


async def test_le_projet_le_plus_couteux_vient_en_premier(base: Path) -> None:
    ventilation = await get_usage_breakdown(base, None)

    assert [p["project_id"] for p in ventilation["per_project"]] == [
        "projet-a",
        "projet-b",
    ]


async def test_borne_a_un_projet_la_ventilation_par_projet_est_vide(base: Path) -> None:
    # Ventiler par projet quand on en regarde un seul n'apprendrait rien.
    ventilation = await get_usage_breakdown(base, "projet-a")

    assert ventilation["per_project"] == []
