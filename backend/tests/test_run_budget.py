"""Plafond de dépense cumulée d'un run autonome — issue #61, ticket-052."""
from pathlib import Path

from tessera.models.agent import AgentResult, AgentRole
from tessera.models.ticket import TicketStatus
from tests.test_orchestrator import (  # réutilise les doubles existants
    _FakeGit,
    _make_agent_result,
    _make_orchestrator,
    _make_ticket,
    _noop,
)


class _CostlyRunner:
    """Runner qui facture un montant fixe à chaque appel d'agent."""

    def __init__(self, cost_per_call: float) -> None:
        self.cost_per_call = cost_per_call
        self.calls = 0

    async def run(self, **kwargs: object) -> AgentResult:
        self.calls += 1
        role = kwargs["role"]
        content = "APPROVED" if role == AgentRole.reviewer else "prose du codeur"
        result = _make_agent_result(content, role=role)  # type: ignore[arg-type]
        return result.model_copy(update={"cost_usd": self.cost_per_call})


async def test_agent_result_porte_son_cout(tmp_path: Path) -> None:
    # Sans coût sur AgentResult, l'orchestrateur ne peut rien agréger : le
    # montant n'existait que dans la branche qui écrit en base.
    assert "cost_usd" in AgentResult.model_fields


async def test_le_run_autonome_s_arrete_au_plafond_cumule(tmp_path: Path) -> None:
    # `LLM_MAX_BUDGET_USD` borne UN appel `query()`. Un clic sur « mode
    # autonome » enchaîne jusqu'à 5 tickets × plusieurs agents : le plafond
    # effectif se chiffrait en dizaines de dollars de quota, sans garde-fou
    # agrégé (issue #61).
    tickets = [_make_ticket(id=f"ticket-00{i}") for i in range(1, 6)]
    orchestrator = _make_orchestrator(
        tmp_path,
        runner=_CostlyRunner(cost_per_call=0.60),
        git_workspace=_FakeGit(),
        project_path=tmp_path,
        tickets=tickets,
        run_max_budget_usd=2.0,
    )

    results = await orchestrator.run_autonomous("projet", max_tickets=5)

    # Chaque ticket coûte 1.20 (codeur + reviewer) : le 2e passe le total à
    # 2.40, au-dessus du plafond, donc le 3e ne démarre pas.
    assert len(results) == 2
    assert orchestrator.spent_usd > 2.0


async def test_sans_plafond_le_run_va_au_bout(tmp_path: Path) -> None:
    tickets = [_make_ticket(id=f"ticket-00{i}") for i in range(1, 4)]
    orchestrator = _make_orchestrator(
        tmp_path,
        runner=_CostlyRunner(cost_per_call=0.60),
        git_workspace=_FakeGit(),
        project_path=tmp_path,
        tickets=tickets,
        run_max_budget_usd=0.0,  # 0 = pas de plafond
    )

    results = await orchestrator.run_autonomous("projet", max_tickets=3)

    assert len(results) == 3


# ------------------------------------------------------------------
# Quota d'abonnement — ticket-054
# ------------------------------------------------------------------


async def test_le_run_autonome_s_arrete_quand_le_quota_est_bas(tmp_path: Path) -> None:
    # `RUN_MAX_BUDGET_USD` borne la dépense *estimée*. Le quota réel est une
    # autre ressource : un run peut être coupé en plein vol sans qu'aucun
    # plafond local n'ait bougé. On s'arrête entre deux tickets plutôt que
    # d'être coupé au milieu d'un (ADR-018).
    from tessera.services.quota_tracker import QuotaSnapshot, QuotaTracker

    tracker = QuotaTracker(low_threshold=0.90)
    tickets = [_make_ticket(id=f"ticket-00{i}") for i in range(1, 4)]
    orchestrator = _make_orchestrator(
        tmp_path,
        runner=_CostlyRunner(cost_per_call=0.0),
        git_workspace=_FakeGit(),
        project_path=tmp_path,
        tickets=tickets,
        quota_tracker=tracker,
    )

    # Le premier ticket passe ; le quota devient bas juste après.
    tracker.record(QuotaSnapshot(status="allowed", utilization=0.10, window="five_hour"))
    results_before = await orchestrator.run_autonomous("projet", max_tickets=1)
    assert len(results_before) == 1

    tracker.record(
        QuotaSnapshot(status="allowed_warning", utilization=0.95, window="five_hour")
    )
    results_after = await orchestrator.run_autonomous("projet", max_tickets=3)

    assert results_after == []


async def test_un_quota_inconnu_ne_bloque_pas_le_run(tmp_path: Path) -> None:
    # Un provider muet doit être indiscernable d'un quota confortable :
    # refuser de travailler faute d'information serait pire que l'ignorer.
    from tessera.services.quota_tracker import QuotaTracker

    tickets = [_make_ticket(id="ticket-001")]
    orchestrator = _make_orchestrator(
        tmp_path,
        runner=_CostlyRunner(cost_per_call=0.0),
        git_workspace=_FakeGit(),
        project_path=tmp_path,
        tickets=tickets,
        quota_tracker=QuotaTracker(),
    )

    results = await orchestrator.run_autonomous("projet", max_tickets=1)

    assert len(results) == 1
