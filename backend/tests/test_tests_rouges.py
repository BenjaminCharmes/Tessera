"""Une suite rouge renvoie au codeur, elle ne va pas en revue — ticket-098."""
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from tessera.models.ticket import (
    Ticket,
    TicketPriority,
    TicketStatus,
    TicketType,
)
from tessera.services.orchestrator import Orchestrator
from tessera.services.pipeline_events import OrchestratorEvent
from tessera.services.test_runner import TestResult


class _FauxTestRunner:
    def __init__(self, resultats: list[bool]) -> None:
        self._resultats = list(resultats)
        self.appels = 0

    async def run_tests(self, project_path: Path, test_command: Any = None, **_: Any) -> TestResult:
        self.appels += 1
        passe = self._resultats.pop(0) if self._resultats else True
        return TestResult(
            passed=passe,
            total=10,
            failed=0 if passe else 3,
            output_summary="10 passed" if passe else "3 failed, 7 passed",
            errors=[] if passe else ["test_x.py::test_truc — AssertionError"],
        )


def _ticket() -> Ticket:
    return Ticket(
        id="ticket-001",
        title="T",
        type=TicketType.feat,
        status=TicketStatus.todo,
        priority=TicketPriority.medium,
        agent="codeur",
        body="corps",
        project_id="p",
        file_path="/w/t.md",
        created="",
    )


def _orchestrateur(tmp_path: Path, runner_tests: _FauxTestRunner, **kw: Any) -> Orchestrator:
    tickets = AsyncMock()
    tickets.get_ticket.return_value = _ticket()
    tickets.update_status.return_value = _ticket()
    git = AsyncMock()
    git.initialiser_base_ref.return_value = None
    git.is_clean.return_value = True
    git.create_branch.return_value = "ticket-001-slug"
    git.current_diff.return_value = "diff --git a/x.py b/x.py\n+x = 1\n"
    git.commit_all.return_value = "abc1234"
    return Orchestrator(
        runner=MagicMock(),
        ticket_service=tickets,
        project_context="ctx",
        agent_configs=[],
        pipeline_log_path=tmp_path / "log.md",
        max_review_rounds=kw.pop("rounds", 2),
        test_runner=runner_tests,
        project_path=tmp_path,
        git_workspace=git,
        **kw,
    )


async def _rien(event: OrchestratorEvent) -> None:
    return None


async def test_une_suite_rouge_n_appelle_pas_le_reviewer(
    tmp_path: Path, monkeypatch: Any
) -> None:
    # Aujourd'hui la sortie des tests était simplement ajoutée au contexte du
    # reviewer : un ticket dont les tests cassent pouvait être approuvé par un
    # reviewer qui n'avait pas regardé la ligne rouge. Un appel de moins, et
    # une garantie de plus.
    revues: list[int] = []

    async def _revue(orch: Any, run: Any, contexte: Any) -> tuple[bool, str, str]:
        revues.append(1)
        return True, "", "APPROVED"

    async def _codeur(orch: Any, run: Any, contexte: Any) -> None:
        return None

    from tessera.services import pipeline_stages as stages

    monkeypatch.setattr(stages, "run_review", _revue)
    monkeypatch.setattr(stages, "run_coder", _codeur)

    runner = _FauxTestRunner([False, False])
    orch = _orchestrateur(tmp_path, runner)

    resultat = await orch.run_pipeline("p", "ticket-001", _rien)

    assert runner.appels == 2, "le codeur doit avoir une seconde chance"
    assert revues == [], "le reviewer ne doit pas être appelé sur une suite rouge"
    assert resultat.approved is False


async def test_le_codeur_recoit_la_raison_de_l_echec(
    tmp_path: Path, monkeypatch: Any
) -> None:
    # Sans l'erreur, le second tour recommence à l'aveugle.
    contextes: list[str] = []

    async def _codeur(orch: Any, run: Any, contexte: Any) -> None:
        contextes.append("\n".join(run.review_feedback))

    async def _revue(orch: Any, run: Any, contexte: Any) -> tuple[bool, str, str]:
        return True, "", "APPROVED"

    from tessera.services import pipeline_stages as stages

    monkeypatch.setattr(stages, "run_coder", _codeur)
    monkeypatch.setattr(stages, "run_review", _revue)

    orch = _orchestrateur(tmp_path, _FauxTestRunner([False, True]))

    await orch.run_pipeline("p", "ticket-001", _rien)

    assert len(contextes) == 2
    assert "AssertionError" in contextes[1]


async def test_une_suite_verte_laisse_le_pipeline_suivre_son_cours(
    tmp_path: Path, monkeypatch: Any
) -> None:
    revues: list[int] = []

    async def _revue(orch: Any, run: Any, contexte: Any) -> tuple[bool, str, str]:
        revues.append(1)
        return True, "", "APPROVED"

    async def _codeur(orch: Any, run: Any, contexte: Any) -> None:
        return None

    from tessera.services import pipeline_stages as stages

    monkeypatch.setattr(stages, "run_review", _revue)
    monkeypatch.setattr(stages, "run_coder", _codeur)

    orch = _orchestrateur(tmp_path, _FauxTestRunner([True]))

    resultat = await orch.run_pipeline("p", "ticket-001", _rien)

    assert revues == [1]
    assert resultat.approved is True


async def test_sans_testeur_rien_ne_change(tmp_path: Path, monkeypatch: Any) -> None:
    # La plupart des projets n'activent pas le testeur : leur pipeline doit
    # se comporter exactement comme avant.
    revues: list[int] = []

    async def _revue(orch: Any, run: Any, contexte: Any) -> tuple[bool, str, str]:
        revues.append(1)
        return True, "", "APPROVED"

    async def _codeur(orch: Any, run: Any, contexte: Any) -> None:
        return None

    from tessera.services import pipeline_stages as stages

    monkeypatch.setattr(stages, "run_review", _revue)
    monkeypatch.setattr(stages, "run_coder", _codeur)

    tickets = AsyncMock()
    tickets.get_ticket.return_value = _ticket()
    tickets.update_status.return_value = _ticket()
    git = AsyncMock()
    git.initialiser_base_ref.return_value = None
    git.is_clean.return_value = True
    git.create_branch.return_value = "b"
    git.current_diff.return_value = "diff"
    git.commit_all.return_value = "abc"
    orch = Orchestrator(
        runner=MagicMock(),
        ticket_service=tickets,
        project_context="ctx",
        agent_configs=[],
        pipeline_log_path=tmp_path / "log.md",
        project_path=tmp_path,
        git_workspace=git,
    )

    resultat = await orch.run_pipeline("p", "ticket-001", _rien)

    assert revues == [1]
    assert resultat.approved is True
