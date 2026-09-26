"""The run budget is checked between rounds, not only between tickets — ticket-191.

`budget_exhausted()` n'était appelé qu'entre deux tickets : avec trois tours
de codeur et de reviewer à 2 $ l'appel, un ticket seul pouvait atteindre
12 $ sans qu'un plafond de run à 5 $ ne bouge.
"""
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from tessera.models.agent import AgentResult, AgentRole
from tessera.models.ticket import TicketStatus
from tests.test_orchestrator import (
    _FakeGit,
    _make_agent_result,
    _make_orchestrator,
    _noop,
)


def _runner_qui_coute(cout_par_appel: float, calls: list[dict[str, Any]]) -> Any:
    """Coder and reviewer each cost `cout_par_appel`; the reviewer never approves."""

    async def fake_run(**kwargs: Any) -> AgentResult:
        calls.append(kwargs)
        role = kwargs["role"]
        content = "CHANGES_REQUESTED: encore" if role == AgentRole.reviewer else "code"
        result = _make_agent_result(content, role)
        result.cost_usd = cout_par_appel
        return result

    runner = MagicMock()
    runner.run = fake_run
    return runner


async def test_un_tour_1_au_dessus_du_plafond_n_ouvre_pas_le_tour_2(
    tmp_path: Path,
) -> None:
    calls: list[dict[str, Any]] = []
    git = _FakeGit()
    orc = _make_orchestrator(
        tmp_path, runner=_runner_qui_coute(3.0, calls), git_workspace=git,
        max_review_rounds=3, run_max_budget_usd=5.0,
    )
    result = await orc.run_pipeline("proj", "ticket-001", _noop)

    tours_codeur = [c for c in calls if c["role"] == AgentRole.codeur]
    assert len(tours_codeur) == 1
    assert result.final_status == TicketStatus.blocked
    assert result.approved is False
    assert result.arret is not None
    assert "6.00" in result.arret and "5.00" in result.arret


async def test_le_travail_du_tour_1_est_commite_en_unapproved_work(
    tmp_path: Path,
) -> None:
    # Le plafond arrête le run, pas le travail déjà payé : ADR-018 exige
    # un arbre propre pour le ticket suivant, et ADR-037 un commit qui dit
    # pourquoi il existe.
    git = _FakeGit()
    orc = _make_orchestrator(
        tmp_path, runner=_runner_qui_coute(3.0, []), git_workspace=git,
        max_review_rounds=3, run_max_budget_usd=5.0,
    )
    await orc.run_pipeline("proj", "ticket-001", _noop)

    assert len(git.commits) == 1
    assert git.commits[0].startswith("chore: ticket-001")
    assert "unapproved work" in git.commits[0]
    assert "budget" in git.commits[0]


async def test_un_plafond_a_zero_ne_borne_rien(tmp_path: Path) -> None:
    calls: list[dict[str, Any]] = []
    orc = _make_orchestrator(
        tmp_path, runner=_runner_qui_coute(3.0, calls), git_workspace=_FakeGit(),
        max_review_rounds=3, run_max_budget_usd=0.0,
    )
    await orc.run_pipeline("proj", "ticket-001", _noop)

    tours_codeur = [c for c in calls if c["role"] == AgentRole.codeur]
    assert len(tours_codeur) == 3


async def test_le_tour_1_demarre_meme_sous_plafond(tmp_path: Path) -> None:
    # Refuser de commencer un ticket est le rôle de la vérification entre
    # tickets ; celle-ci ne coupe qu'un tour suivant.
    calls: list[dict[str, Any]] = []
    orc = _make_orchestrator(
        tmp_path, runner=_runner_qui_coute(3.0, calls), git_workspace=_FakeGit(),
        max_review_rounds=3, run_max_budget_usd=5.0,
    )
    orc.record_spend(10.0)
    await orc.run_pipeline("proj", "ticket-001", _noop)

    assert any(c["role"] == AgentRole.codeur for c in calls)
