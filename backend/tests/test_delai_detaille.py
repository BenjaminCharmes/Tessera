"""A test timeout names the step that overran and what each step took — ticket-514."""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services import pipeline_stages
from tessera.services.detail_du_delai import detail_du_delai, ligne_de_delai, nom_court
from tessera.services.pipeline_reprise import _TESTS_SANS_RESULTAT, verifier_travail_repris
from tessera.services.pipeline_run import PipelineRun
from tessera.services.test_runner import (
    EtapeCoupee,
    EtapeTest,
    TestResult,
    TestRunnerService,
)

PY = f'"{sys.executable}" -c'
_RAPIDE = f'{PY} "pass"'
_LENTE = f'{PY} "import time; time.sleep(60)"'


def _expiree() -> TestResult:
    return TestResult(
        passed=False,
        expiree=True,
        total=0,
        failed=0,
        output_summary=(
            "Timeout après 420s — suite\n"
            "Étapes : install 6 s, lint 28 s, check:build coupé après 190 s"
        ),
        etapes=[EtapeTest("pnpm install", 0, 6000), EtapeTest("pnpm run lint", 0, 28000)],
        etape_coupee=EtapeCoupee("pnpm run check:build", 190000),
        delai_s=420.0,
    )


async def test_each_finished_step_carries_its_duration(tmp_path: Path) -> None:
    pause = f'{PY} "import time; time.sleep(0.3)"'
    result = await TestRunnerService().run_tests(tmp_path, test_command=f"{_RAPIDE} && {pause}")

    assert result.passed is True
    assert result.etapes[1].duree_ms >= 250
    assert all(e.duree_ms >= 0 for e in result.etapes)


async def test_an_expired_run_names_the_cut_step_and_its_time(tmp_path: Path) -> None:
    result = await TestRunnerService().run_tests(
        tmp_path, test_command=f"{_RAPIDE} && {_LENTE}", timeout=4
    )

    assert result.expiree is True
    assert result.etape_coupee is not None
    assert "time.sleep(60)" in result.etape_coupee.commande
    assert result.etape_coupee.duree_ms >= 2000
    assert "coupé après" in result.output_summary
    assert result.output_summary.startswith("Timeout après 4s")


async def test_an_expired_run_lists_the_steps_finished_before_the_cut(tmp_path: Path) -> None:
    # Délai large : sous charge, un démarrage de Python dépasse 2 s, et un délai
    # de 4 s coupait la deuxième étape rapide avant sa fin.
    result = await TestRunnerService().run_tests(
        tmp_path, test_command=f"{_RAPIDE} && {_RAPIDE} && {_LENTE}", timeout=15
    )

    assert result.expiree is True
    assert len(result.etapes) == 2
    assert all(e.code == 0 and e.duree_ms >= 0 for e in result.etapes)
    assert result.delai_s == 15.0


def test_the_detail_lists_finished_steps_then_the_cut_one() -> None:
    assert detail_du_delai(_expiree()) == "install 6 s, lint 28 s, check:build coupé après 190 s"


def test_the_log_line_gives_the_limit_and_every_step() -> None:
    assert ligne_de_delai(_expiree()) == (
        "délai dépassé (420 s) — install 6 s, lint 28 s, check:build coupé après 190 s"
    )


def test_the_log_line_without_known_steps_keeps_the_limit_only() -> None:
    nu = TestResult(passed=False, expiree=True, total=0, failed=0, output_summary="t", delai_s=60.0)

    assert ligne_de_delai(nu) == "délai dépassé (60 s)"


def test_a_step_label_falls_back_to_the_executable_for_an_inline_script() -> None:
    assert nom_court("pnpm run lint") == "lint"
    assert nom_court("uv run pytest") == "pytest"
    assert nom_court(f'{PY} "import time; time.sleep(60)"').startswith("python")
    assert nom_court("pytest -q") == "pytest"


def _orch_et_run(tmp_path: Path, resultats: list[TestResult]) -> tuple[MagicMock, PipelineRun]:
    runner = MagicMock()
    runner.run_tests = AsyncMock(side_effect=resultats)
    orch = MagicMock()
    orch._test_runner = runner
    orch._project_path = tmp_path
    orch._test_command = None
    orch._log = MagicMock()
    ticket = Ticket(
        id="ticket-000",
        title="t",
        type=TicketType.feat,
        status=TicketStatus.in_progress,
        priority=TicketPriority.medium,
        agent="codeur",
    )
    return orch, PipelineRun(project_id="p", ticket=ticket, on_event=AsyncMock())


async def test_the_pipeline_log_carries_the_duration_of_each_step(tmp_path: Path) -> None:
    orch, run = _orch_et_run(tmp_path, [_expiree(), _expiree()])

    await pipeline_stages.run_tests(orch, run, reprise=True)

    lignes = [c.args[0] for c in orch._log.call_args_list]
    attendu = (
        "[ticket-000] testeur: délai dépassé (420 s) — "
        "install 6 s, lint 28 s, check:build coupé après 190 s"
    )
    assert attendu in lignes
    assert len([ligne for ligne in lignes if "délai dépassé (420 s)" in ligne]) == 2


async def test_the_stage_context_holds_the_list_once(tmp_path: Path) -> None:
    orch, run = _orch_et_run(tmp_path, [_expiree(), _expiree()])

    retour = await pipeline_stages.run_tests(orch, run, reprise=True)

    assert retour is False
    assert run.test_context.count("install 6 s") == 1


async def test_the_coder_feedback_after_a_resumed_timeout_holds_the_list(tmp_path: Path) -> None:
    # Ce que lit le codeur, c'est `review_feedback` : `test_context` est vidé
    # par l'appelant avant le tour.
    orch, run = _orch_et_run(tmp_path, [_expiree(), _expiree()])
    orch._git_workspace.commits_repris = 1

    vert = await verifier_travail_repris(orch, run)

    assert vert is False
    assert len(run.review_feedback) == 1
    retour = run.review_feedback[0]
    assert retour.startswith(_TESTS_SANS_RESULTAT)
    assert "install 6 s, lint 28 s, check:build coupé après 190 s" in retour
    assert run.test_context == ""


async def test_a_resumed_run_without_step_detail_keeps_the_fixed_feedback(tmp_path: Path) -> None:
    nu = TestResult(passed=False, expiree=True, total=0, failed=0, output_summary="t")
    orch, run = _orch_et_run(tmp_path, [nu, nu])
    orch._git_workspace.commits_repris = 1

    await verifier_travail_repris(orch, run)

    assert run.review_feedback == [_TESTS_SANS_RESULTAT]
