"""Un ticket qui le déclare passe par un tour de plan avant le code — ticket-243."""
from pathlib import Path

import pytest

from tessera.config import settings
from tessera.models.agent import AgentConfig, AgentResult, AgentRole
from tessera.services.agent_runner import OUTILS_DE_RELECTURE
from tessera.services.pipeline_events import EventType, OrchestratorEvent
from tessera.services.ticket_service import TicketService
from tests.test_orchestrator import (
    _FakeGit,
    _make_agent_result,
    _make_orchestrator,
    _make_ticket,
    _noop,
)

_PLAN = "1. Lire `x.py`\n2. Ajouter `y`\n- critère 1 : couvert par l'étape 2"


class _Runner:
    """Rend un plan au rôle `plan`, et enregistre chaque appel."""

    def __init__(self, plan_leve: bool = False) -> None:
        self.calls: list[dict[str, object]] = []
        self._plan_leve = plan_leve

    async def run(self, **kwargs: object) -> AgentResult:
        self.calls.append(kwargs)
        role = kwargs["role"]
        if role == "plan":
            if self._plan_leve:
                raise RuntimeError("provider indisponible")
            return _make_agent_result(_PLAN)
        return _make_agent_result("APPROVED" if role == AgentRole.reviewer else "fait")


def _svc(plan: bool):  # type: ignore[no-untyped-def]
    from unittest.mock import AsyncMock

    ticket = _make_ticket(plan=plan)
    svc = AsyncMock()
    svc.get_ticket.return_value = ticket
    svc.update_status.return_value = ticket
    return svc


def _roles(runner: _Runner) -> list[object]:
    return [c["role"] for c in runner.calls]


async def test_un_ticket_a_plan_passe_par_le_plan_avant_le_codeur(tmp_path: Path) -> None:
    runner = _Runner()
    orc = _make_orchestrator(
        tmp_path, runner=runner, ticket_service=_svc(plan=True),  # type: ignore[arg-type]
        git_workspace=_FakeGit(),
        agent_configs=[AgentConfig(
            role="codeur", model="modele-du-codeur", max_tokens=100, prompt_file="codeur.md"
        )],
    )

    result = await orc.run_pipeline("proj", "ticket-001", _noop)

    assert result.approved is True
    assert _roles(runner) == ["plan", AgentRole.codeur, AgentRole.reviewer]
    config_plan = runner.calls[0]["agent_config"]
    assert isinstance(config_plan, AgentConfig)
    assert config_plan.model == "modele-du-codeur"
    # Le plan part au codeur et au reviewer : l'un le suit, l'autre juge l'écart.
    for appel in runner.calls[1:]:
        assert "## Plan retenu avant le code" in str(appel["project_context"])
        assert _PLAN in str(appel["project_context"])


async def test_sans_plan_declare_rien_ne_change(tmp_path: Path) -> None:
    runner = _Runner()
    orc = _make_orchestrator(
        tmp_path, runner=runner, ticket_service=_svc(plan=False),  # type: ignore[arg-type]
        git_workspace=_FakeGit(),
    )

    await orc.run_pipeline("proj", "ticket-001", _noop)

    assert _roles(runner) == [AgentRole.codeur, AgentRole.reviewer]
    assert "Plan retenu" not in str(runner.calls[0]["project_context"])


async def test_un_plan_qui_echoue_n_arrete_pas_le_run(tmp_path: Path) -> None:
    runner = _Runner(plan_leve=True)
    orc = _make_orchestrator(
        tmp_path, runner=runner, ticket_service=_svc(plan=True),  # type: ignore[arg-type]
        git_workspace=_FakeGit(),
    )

    result = await orc.run_pipeline("proj", "ticket-001", _noop)

    assert result.approved is True
    assert _roles(runner) == ["plan", AgentRole.codeur, AgentRole.reviewer]


async def test_le_plan_se_voit_dans_le_fil_du_codeur(tmp_path: Path) -> None:
    events: list[OrchestratorEvent] = []

    async def _collecte(event: OrchestratorEvent) -> None:
        events.append(event)

    orc = _make_orchestrator(
        tmp_path, runner=_Runner(), ticket_service=_svc(plan=True),  # type: ignore[arg-type]
        git_workspace=_FakeGit(),
    )

    await orc.run_pipeline("proj", "ticket-001", _collecte)

    fins = [
        e for e in events
        if e.type == EventType.AGENT_DONE and e.data.get("phase") == "plan"
    ]
    assert len(fins) == 1
    assert fins[0].agent == AgentRole.codeur
    assert fins[0].data["content"] == _PLAN


@pytest.mark.parametrize(("valeur", "attendu"), [("true", True), ("false", False), ('"oui"', False)])
async def test_le_frontmatter_declare_le_plan(
    tmp_path: Path, valeur: str, attendu: bool
) -> None:
    dossier = tmp_path / "tickets" / "todo"
    dossier.mkdir(parents=True)
    (dossier / "ticket-001-x.md").write_text(
        "---\nid: ticket-001\ntitle: \"x\"\ntype: feat\nstatus: todo\npriority: medium\n"
        f"agent: codeur\nplan: {valeur}\n---\n\n# x\n",
        encoding="utf-8",
    )

    ticket = await TicketService(tmp_path, "p").get_ticket("ticket-001")

    assert ticket is not None
    assert ticket.plan is attendu


async def test_le_plan_n_a_que_les_outils_de_lecture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tessera.routers.orchestrator import _build_orchestrator

    monkeypatch.setattr(settings, "ide_workspace_dir", tmp_path)
    monkeypatch.setattr(settings, "llm_provider", "agent_sdk")
    projet = tmp_path / "mon-projet"
    projet.mkdir()
    (projet / "CLAUDE.md").write_text("# p\n", encoding="utf-8")

    orchestrator = await _build_orchestrator("mon-projet")

    provider = orchestrator._runner._provider_pour("plan")
    assert provider._allowed_tools == OUTILS_DE_RELECTURE  # type: ignore[attr-defined]
