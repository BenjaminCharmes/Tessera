"""`worktree.setup` runs in the worktree before the coder, and a failure blocks the run — ticket-536."""
import json
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.models.worktree_config import ConfigWorktree
from tessera.services import preparation_worktree
from tessera.services.commande_effective import PlaceholderInconnu, setup_effectif
from tessera.services.orchestrator import Orchestrator
from tessera.services.pipeline_events import EventType, OrchestratorEvent
from tessera.services.pipeline_run import PipelineRun
from tessera.services.politique_run import PolitiqueRun
from tessera.services.preparation_worktree import (
    ResultatPreparation,
    preparation_du_run,
    preparer_le_worktree,
)
from tessera.services.run_dans_worktree import adopter_la_branche
from tessera.services.run_worktree import RunWorktree
from tessera.services.test_runner import EtapeTest, TestResult
from tessera.services.worktree_politique import lire_worktree

_DEPOT = Path("/depot")
_WT = RunWorktree(racine=Path("/wt/demo/ticket-1"), projet=Path("/wt/demo/ticket-1"), branche="b")


class _Lanceur:
    """Stands in for `TestRunnerService`: records how it was built and called."""

    construits: list[dict[str, object]] = []
    appels: list[tuple[Path, str | None]] = []
    resultat: TestResult = TestResult(passed=True, total=0, failed=0, output_summary="OK")

    def __init__(
        self, cwd: str | None = None, timeout: int | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        _Lanceur.construits.append({"cwd": cwd, "timeout": timeout, "env": env})

    async def run_tests(self, project_path: Path, test_command: str | None = None) -> TestResult:
        _Lanceur.appels.append((project_path, test_command))
        return _Lanceur.resultat


@pytest.fixture(autouse=True)
def lanceur(monkeypatch: pytest.MonkeyPatch) -> None:
    _Lanceur.construits = []
    _Lanceur.appels = []
    _Lanceur.resultat = TestResult(passed=True, total=0, failed=0, output_summary="OK")
    monkeypatch.setattr(preparation_worktree, "TestRunnerService", _Lanceur)


def _politique(setup: str | None, env: dict[str, str] | None = None) -> PolitiqueRun:
    return PolitiqueRun(worktree=ConfigWorktree(setup=setup, env=env or {}))


def _declarer(dossier: Path, worktree: dict[str, object]) -> ConfigWorktree | None:
    (dossier / "agents.json").write_text(json.dumps({"worktree": worktree}), encoding="utf-8")
    return lire_worktree(dossier, dossier, "tracked")


def test_setup_is_read_from_agents_json(tmp_path: Path) -> None:
    config = _declarer(tmp_path, {"setup": "corepack pnpm@10 install --frozen-lockfile"})
    assert config is not None
    assert config.setup == "corepack pnpm@10 install --frozen-lockfile"


def test_setup_defaults_to_none(tmp_path: Path) -> None:
    config = _declarer(tmp_path, {})
    assert config is not None
    assert config.setup is None


def test_a_setup_that_is_not_a_string_invalidates_the_declaration(tmp_path: Path) -> None:
    assert _declarer(tmp_path, {"setup": ["pnpm", "install"]}) is None


def test_setup_effectif_resolves_placeholders_and_ignores_blank() -> None:
    config = ConfigWorktree(setup="make -C {worktree}")
    assert setup_effectif(config, Path("/wt"), _DEPOT) == "make -C /wt"
    assert setup_effectif(ConfigWorktree(setup="  "), Path("/wt"), _DEPOT) is None
    with pytest.raises(PlaceholderInconnu):
        setup_effectif(ConfigWorktree(setup="{faute}"), Path("/wt"), _DEPOT)


async def test_setup_runs_in_the_worktree_with_its_env_and_the_tester_timeout() -> None:
    env = {"CI": "1"}
    preparation = preparation_du_run(_politique("pnpm install", env), _WT.racine, _DEPOT, env, 900)
    assert preparation is not None
    assert (await preparation()).arret is None
    assert _Lanceur.construits == [{"cwd": None, "timeout": 900, "env": env}]
    assert _Lanceur.appels == [(_WT.racine, "pnpm install")]


def test_a_project_without_setup_has_no_preparation() -> None:
    assert preparation_du_run(_politique(None), _WT.racine, _DEPOT, None, None) is None
    assert preparation_du_run(PolitiqueRun(), _WT.racine, _DEPOT, None, None) is None
    assert preparation_du_run(_politique("x"), None, _DEPOT, None, None) is None
    assert _Lanceur.construits == [] and _Lanceur.appels == []


async def test_a_failed_setup_returns_the_command_and_its_output() -> None:
    _Lanceur.resultat = TestResult(
        passed=False, total=0, failed=0, output_summary="FAILED (exit 1)",
        failure_details="ERR_PNPM_NO_LOCKFILE", etapes=[EtapeTest("pnpm install", 1)],
    )
    preparation = preparation_du_run(_politique("pnpm install"), _WT.racine, _DEPOT, None, None)
    assert preparation is not None
    arret = (await preparation()).arret
    assert arret is not None
    assert "pnpm install" in arret and "ERR_PNPM_NO_LOCKFILE" in arret


async def test_an_expired_setup_says_so() -> None:
    _Lanceur.resultat = TestResult(
        passed=False, expiree=True, total=0, failed=0, output_summary="Timeout après 60s"
    )
    preparation = preparation_du_run(_politique("pnpm install"), _WT.racine, _DEPOT, None, None)
    assert preparation is not None
    assert "délai dépassé" in str((await preparation()).arret)


class _Tickets:
    def __init__(self) -> None:
        self.statuts: list[TicketStatus] = []

    async def update_status(self, _ticket_id: str, statut: TicketStatus) -> None:
        self.statuts.append(statut)


def _run(evenements: list[OrchestratorEvent]) -> PipelineRun:
    async def on_event(evenement: OrchestratorEvent) -> None:
        evenements.append(evenement)

    ticket = Ticket(
        id="ticket-1", title="t", type=TicketType.feat, status=TicketStatus.todo,
        priority=TicketPriority.medium, agent="codeur",
    )
    return PipelineRun(project_id="demo", ticket=ticket, on_event=on_event)


def _orchestrateur(
    journal: list[str], arret: str | None, lignes: list[str] | None = None,
    code: int | None = 0,
) -> tuple[Orchestrator, _Tickets]:
    tickets = _Tickets()
    lignes = [] if lignes is None else lignes

    async def adopter(branche: str, _base: str) -> str:
        journal.append("branche")
        return branche

    async def preparer() -> ResultatPreparation:
        journal.append("setup")
        return ResultatPreparation("pnpm install", 1830, code, arret)

    orch = SimpleNamespace(
        _worktree=_WT, _git_workspace=SimpleNamespace(adopter_worktree=adopter),
        _base_branch="develop", _chemins_absents=(), _log=lignes.append,
        _preparation=preparer, _ticket_svc=tickets,
    )
    return cast(Orchestrator, orch), tickets


async def test_the_setup_runs_after_the_branch_and_lets_the_run_go_on_to_the_coder() -> None:
    journal: list[str] = []
    orch, tickets = _orchestrateur(journal, None)
    assert await adopter_la_branche(orch, _run([])) is None
    assert journal == ["branche", "setup"]
    assert tickets.statuts == []


async def test_a_failed_setup_blocks_the_run_before_the_coder() -> None:
    journal: list[str] = []
    evenements: list[OrchestratorEvent] = []
    orch, tickets = _orchestrateur(journal, "La préparation du worktree a échoué : `x`")
    resultat = await adopter_la_branche(orch, _run(evenements))
    assert resultat is not None
    assert resultat.final_status == TicketStatus.blocked and not resultat.approved
    assert resultat.arret == "La préparation du worktree a échoué : `x`"
    assert tickets.statuts == [TicketStatus.blocked]
    assert EventType.ERROR in [e.type for e in evenements]


async def test_without_preparation_nothing_runs_before_the_coder() -> None:
    orch = cast(Orchestrator, SimpleNamespace(_preparation=None))
    assert await preparer_le_worktree(orch, _run([])) is None


async def test_a_successful_setup_emits_its_event_and_writes_its_log_line() -> None:
    evenements: list[OrchestratorEvent] = []
    lignes: list[str] = []
    orch, _ = _orchestrateur([], None, lignes)
    assert await preparer_le_worktree(orch, _run(evenements)) is None
    setup = [e for e in evenements if e.type == EventType.WORKTREE_SETUP]
    assert len(setup) == 1
    assert setup[0].data == {"command": "pnpm install", "duration_ms": 1830, "exit_code": 0}
    assert lignes == ["[ticket-1] préparation: ok — `pnpm install` (code 0, 1830 ms)"]


async def test_a_failed_setup_emits_its_event_and_line_before_blocking() -> None:
    evenements: list[OrchestratorEvent] = []
    lignes: list[str] = []
    orch, tickets = _orchestrateur([], "échec", lignes, code=1)
    resultat = await preparer_le_worktree(orch, _run(evenements))
    assert resultat is not None and resultat.final_status == TicketStatus.blocked
    types = [e.type for e in evenements]
    assert types.index(EventType.WORKTREE_SETUP) < types.index(EventType.ERROR)
    setup = next(e for e in evenements if e.type == EventType.WORKTREE_SETUP)
    assert setup.data["exit_code"] == 1
    assert lignes == ["[ticket-1] préparation: échec — `pnpm install` (code 1, 1830 ms)"]
    assert tickets.statuts == [TicketStatus.blocked]


async def test_a_setup_that_never_started_has_no_exit_code() -> None:
    lignes: list[str] = []
    orch, _ = _orchestrateur([], "non démarrée", lignes, code=None)
    await preparer_le_worktree(orch, _run([]))
    assert lignes == ["[ticket-1] préparation: échec — `pnpm install` (code aucun, 1830 ms)"]


async def test_the_real_preparation_reports_command_duration_and_exit_code() -> None:
    _Lanceur.resultat = TestResult(
        passed=True, total=0, failed=0, output_summary="OK", duration_ms=42,
        etapes=[EtapeTest("pnpm install", 0)],
    )
    preparation = preparation_du_run(_politique("pnpm install"), _WT.racine, _DEPOT, None, None)
    assert preparation is not None
    assert await preparation() == ResultatPreparation("pnpm install", 42, 0, None)


async def test_a_project_without_setup_emits_no_event_and_no_line() -> None:
    evenements: list[OrchestratorEvent] = []
    lignes: list[str] = []
    orch = cast(Orchestrator, SimpleNamespace(_preparation=None, _log=lignes.append))
    assert await preparer_le_worktree(orch, _run(evenements)) is None
    assert evenements == [] and lignes == []
