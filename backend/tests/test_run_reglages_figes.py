"""A run keeps the budgets and the dialogue delay it opened with — ticket-806 (ADR-075).

Un plafond changé sous un run qui le dépasse est pire qu'un plafond fixe : les
valeurs sont lues une fois, à l'ouverture, et la tâche du run en hérite.
"""
import asyncio
import dataclasses
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from tessera import reglages
from tessera.config import settings
from tessera.routers import orchestrator as routeur
from tessera.routers.orchestrator import RunRequest, get_limits, run_pipeline
from tessera.services.pipeline import run_executor
from tessera.services.noyau.database import init_db
from tessera.services.noyau.pipeline_events import EventType, OrchestratorEvent
from tessera.services.providers import par_role
from tessera.services.providers.par_role import provider_pour_role
from tessera.services.pipeline.run_registry import RUN_REGISTRY, RunActif, RunRegistry
from tests.test_providers_base import FakeProvider


@pytest.fixture(autouse=True)
def _etat_propre() -> Iterator[None]:
    """No override and no pinned snapshot, before and after each test."""
    reglages._SURCHARGES.clear()
    reglages._SNAPSHOT.set(None)
    yield
    reglages._SURCHARGES.clear()
    reglages._SNAPSHOT.set(None)


@pytest.fixture
async def base(tmp_path: Path) -> Path:
    chemin = tmp_path / "tessera.db"
    await init_db(chemin)
    return chemin


@pytest.fixture
def appels_de_fabrique(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    appels: list[dict[str, Any]] = []

    def fausse(name: str | None = None, api_key: str = "", **kwargs: Any) -> FakeProvider:
        appels.append({"name": name, **kwargs})
        return FakeProvider()

    monkeypatch.setattr(par_role, "get_provider", fausse)
    return appels


@pytest.fixture
def lancement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[dict[str, Any]]:
    """`run_pipeline` with a fake assembly and a fake executor that record what they read."""
    ws = tmp_path / "workspace"
    (ws / "mon-projet").mkdir(parents=True)
    (ws / "mon-projet" / "CLAUDE.md").write_text("# mon-projet\n", encoding="utf-8")
    monkeypatch.setattr(settings, "ide_workspace_dir", ws)
    vu: dict[str, Any] = {}

    async def assemblage(project_id: str, *args: object, **kwargs: object) -> object:
        vu["a_la_construction"] = reglages.courants().run_max_budget_usd
        if "avant_lecture" in vu:
            await vu["avant_lecture"]()
            vu["apres_ecriture"] = reglages.courants().run_max_budget_usd
        return object()

    async def executeur(run: RunActif, *args: object, **kwargs: object) -> None:
        vu["dans_la_tache"] = reglages.courants()
        RUN_REGISTRY.fermer(run.run_id)

    monkeypatch.setattr(routeur, "manques_avant_depart", lambda *a, **k: [])
    monkeypatch.setattr(routeur, "build_orchestrator", assemblage)
    monkeypatch.setattr(routeur, "executer", executeur)
    yield vu
    for run_id in [r["run_id"] for r in RUN_REGISTRY.instantane()]:
        RUN_REGISTRY.fermer(run_id)


async def _lancer() -> None:
    await run_pipeline(RunRequest(project_id="mon-projet", ticket_id="ticket-001"))
    await asyncio.gather(*list(routeur._TACHES))


def test_ouvrir_stores_the_values_of_the_moment_in_the_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "run_max_budget_usd", 6.5)
    monkeypatch.setattr(settings, "dialogue_timeout_s", 90.0)
    registre = RunRegistry()

    run = registre.ouvrir("projet", "ticket-001")
    monkeypatch.setattr(settings, "run_max_budget_usd", 9.0)
    registre.fermer(run.run_id)

    assert run.reglages.run_max_budget_usd == 6.5
    assert run.reglages.dialogue_timeout_s == 90.0
    assert "reglages" not in run.en_dict()


async def test_orchestrator_gets_the_run_budget_frozen_at_opening(
    lancement: dict[str, Any], base: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "run_max_budget_usd", 5.0)

    async def changer() -> None:
        await reglages.ecrire(base, "run_max_budget_usd", 20.0)

    lancement["avant_lecture"] = changer
    await _lancer()

    assert lancement["a_la_construction"] == 5.0
    assert lancement["apres_ecriture"] == 5.0
    assert reglages.du_moment().run_max_budget_usd == 20.0


async def test_dialogue_channel_uses_the_frozen_timeout(
    base: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "dialogue_timeout_s", 0.01)
    reglages.figer()
    await reglages.ecrire(base, "dialogue_timeout_s", 3000.0)
    recus: list[OrchestratorEvent] = []

    async def envoyer(event: OrchestratorEvent) -> None:
        recus.append(event)

    canal = run_executor.dialogue_du_run(
        envoyer, RunActif(run_id="r1", project_id="p", ticket_id="ticket-001")
    )
    # Le délai figé (0,01 s) est écoulé : la question se résout seule, tout de suite.
    await asyncio.wait_for(canal.ask("On casse l'API ?"), timeout=5)

    assert canal._timeout_s == 0.01
    assert any(e.type is EventType.AGENT_QUESTION for e in recus)


def test_provider_budget_follows_the_frozen_value_inside_a_run_and_the_live_one_outside(
    appels_de_fabrique: list[dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    projet = tmp_path / "inexistant"
    monkeypatch.setattr(settings, "llm_max_budget_usd", 3.0)
    reglages.figer()

    monkeypatch.setattr(settings, "llm_max_budget_usd", 4.0)
    provider_pour_role(projet, "codeur")
    reglages._SNAPSHOT.set(None)
    provider_pour_role(projet, "codeur")

    assert [a["max_budget_usd"] for a in appels_de_fabrique] == [3.0, 4.0]


async def test_a_task_created_after_figer_inherits_the_snapshot(
    base: Path,
) -> None:
    figees = dataclasses.replace(reglages.du_moment(), run_max_budget_usd=11.0)
    reglages.figer(figees)
    await reglages.ecrire(base, "run_max_budget_usd", 30.0)

    async def lire() -> float:
        return reglages.courants().run_max_budget_usd

    assert await asyncio.create_task(lire()) == 11.0


async def test_a_second_run_opened_after_ecrire_gets_the_new_values(
    lancement: dict[str, Any], base: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "run_max_budget_usd", 5.0)
    await _lancer()
    premier = lancement["dans_la_tache"].run_max_budget_usd
    reglages._SNAPSHOT.set(None)

    await reglages.ecrire(base, "run_max_budget_usd", 20.0)
    await _lancer()

    assert premier == 5.0
    assert lancement["dans_la_tache"].run_max_budget_usd == 20.0
    assert lancement["a_la_construction"] == 20.0


async def test_get_limits_returns_the_current_values(
    base: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "llm_max_budget_usd", 2.0)
    await reglages.ecrire(base, "run_max_budget_usd", 12.0)

    limites = await get_limits()

    assert limites.run_max_budget_usd == 12.0
    assert limites.llm_max_budget_usd == 2.0
