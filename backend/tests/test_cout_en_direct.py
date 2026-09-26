"""A run's cost can be read while it runs — ticket-197.

Le coût n'apparaissait qu'après coup ; `RunActif.cout_usd` existait et rien
ne le remplissait. C'est pendant le run qu'on décide de l'arrêter.
"""
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from tessera.config import settings
from tessera.main import app
from tessera.models.agent import AgentResult, AgentRole
from tessera.services.pipeline_events import EventType, OrchestratorEvent
from tessera.services.run_executor import _suivre
from tessera.services.run_registry import RunActif
from tests.test_orchestrator import _make_agent_result, _make_orchestrator


def _ev(type_: EventType, agent: AgentRole | None = None, **data: Any) -> OrchestratorEvent:
    return OrchestratorEvent(type=type_, agent=agent, ticket_id="ticket-001", data=data)


def test_agent_done_cumule_le_cout_et_compte_les_appels() -> None:
    run = RunActif(run_id="r1", project_id="p")
    _suivre(run, _ev(EventType.AGENT_DONE, AgentRole.codeur, cost_usd=0.4))
    _suivre(run, _ev(EventType.AGENT_DONE, AgentRole.reviewer, cost_usd=0.2))
    assert run.cout_usd == pytest.approx(0.6)
    assert run.appels == 2


def test_le_compteur_d_outils_repart_a_zero_a_chaque_agent() -> None:
    # C'est le compteur qui bouge en temps réel : il doit parler de l'agent en
    # cours, pas de tout le run.
    run = RunActif(run_id="r1", project_id="p")
    _suivre(run, _ev(EventType.AGENT_STARTED, AgentRole.codeur))
    for _ in range(3):
        _suivre(run, _ev(EventType.AGENT_TOOL_USE, AgentRole.codeur, tool="Read"))
    assert run.outils == 3
    _suivre(run, _ev(EventType.AGENT_STARTED, AgentRole.reviewer))
    assert run.outils == 0


def test_l_instantane_porte_le_cout_les_appels_et_les_outils() -> None:
    # Un F5 pendant le run doit retrouver le cumul, pas repartir de zéro.
    run = RunActif(run_id="r1", project_id="p", cout_usd=0.84, appels=3, outils=47)
    d = run.en_dict()
    assert (d["cout_usd"], d["appels"], d["outils"]) == (0.84, 3, 47)


async def test_agent_done_du_pipeline_porte_le_cout_de_l_appel(tmp_path: Path) -> None:
    async def fake_run(**kwargs: Any) -> AgentResult:
        role = kwargs["role"]
        result = _make_agent_result("APPROVED" if role == AgentRole.reviewer else "code", role)
        result.cost_usd = 0.4 if role == AgentRole.codeur else 0.2
        return result

    runner = MagicMock()
    runner.run = fake_run
    couts: list[float] = []

    async def capture(ev: OrchestratorEvent) -> None:
        if ev.type is EventType.AGENT_DONE:
            couts.append(float(ev.data["cost_usd"]))

    orc = _make_orchestrator(tmp_path, runner=runner)
    await orc.run_pipeline("proj", "ticket-001", capture)
    assert couts == [0.4, 0.2]


def test_l_endpoint_des_plafonds_rend_les_reglages(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "run_max_budget_usd", 5.0)
    monkeypatch.setattr(settings, "llm_max_budget_usd", 2.0)
    body = TestClient(app).get("/api/v1/orchestrator/limits").json()
    assert body == {"run_max_budget_usd": 5.0, "llm_max_budget_usd": 2.0}
