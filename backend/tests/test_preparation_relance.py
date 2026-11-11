"""ticket-906: own setup timeout, and one retry when the setup timed out."""
import json
from pathlib import Path

import pytest

from tessera.models.worktree_config import ConfigWorktree
from tessera.services.gardes.politique_run import PolitiqueRun
from tessera.services.gardes.worktree_politique import lire_worktree
from tessera.services.noyau.pipeline_events import EventType, OrchestratorEvent
from tessera.services.pipeline import preparation_worktree
from tessera.services.pipeline.preparation_run import delai_du_setup
from tessera.services.pipeline.preparation_worktree import preparation_du_run, preparer_le_worktree
from tessera.services.verification.test_runner import EtapeTest, TestResult
from tests.test_preparation_worktree import _DEPOT, _WT, _orchestrateur, _run

_OK = TestResult(passed=True, total=0, failed=0, output_summary="OK")
_DELAI = TestResult(passed=False, expiree=True, total=0, failed=0, output_summary="Timeout")
_CODE_1 = TestResult(
    passed=False, total=0, failed=0, output_summary="FAILED", etapes=[EtapeTest("x", 1)]
)


class _Sequence:
    """Stands in for `TestRunnerService`: answers from a list, in order."""

    resultats: list[TestResult] = []
    appels: int = 0
    timeouts: list[int | None] = []

    def __init__(
        self, cwd: str | None = None, timeout: int | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        _Sequence.timeouts.append(timeout)

    async def run_tests(self, project_path: Path, test_command: str | None = None) -> TestResult:
        _Sequence.appels += 1
        return _Sequence.resultats.pop(0)


@pytest.fixture(autouse=True)
def sequence(monkeypatch: pytest.MonkeyPatch) -> None:
    _Sequence.resultats = []
    _Sequence.appels = 0
    _Sequence.timeouts = []
    monkeypatch.setattr(preparation_worktree, "TestRunnerService", _Sequence)


def _declarer(dossier: Path, valeur: object) -> ConfigWorktree | None:
    (dossier / "agents.json").write_text(
        json.dumps({"worktree": {"setup_timeout_s": valeur}}), encoding="utf-8"
    )
    return lire_worktree(dossier, dossier, "tracked")


def test_setup_timeout_is_read_from_agents_json(tmp_path: Path) -> None:
    config = _declarer(tmp_path, 600)
    assert config is not None and config.setup_timeout_s == 600


@pytest.mark.parametrize("valeur", ["60", 1.5, -1, 0, True])
def test_a_bad_setup_timeout_invalidates_the_declaration(tmp_path: Path, valeur: object) -> None:
    assert _declarer(tmp_path, valeur) is None


def test_compte_agent_defaults_to_false_and_reads_a_boolean(tmp_path: Path) -> None:
    (tmp_path / "agents.json").write_text(json.dumps({"worktree": {}}), encoding="utf-8")
    config = lire_worktree(tmp_path, tmp_path, "tracked")
    assert config is not None and config.compte_agent is False
    (tmp_path / "agents.json").write_text(
        json.dumps({"worktree": {"compte_agent": True}}), encoding="utf-8"
    )
    config = lire_worktree(tmp_path, tmp_path, "tracked")
    assert config is not None and config.compte_agent is True


@pytest.mark.parametrize("valeur", ["oui", 1, 0, None, []])
def test_a_non_boolean_compte_agent_invalidates_the_declaration(
    tmp_path: Path, valeur: object
) -> None:
    (tmp_path / "agents.json").write_text(
        json.dumps({"worktree": {"compte_agent": valeur}}), encoding="utf-8"
    )
    assert lire_worktree(tmp_path, tmp_path, "tracked") is None


def test_delai_du_setup_prefers_the_declared_timeout() -> None:
    declare = PolitiqueRun(worktree=ConfigWorktree(setup="x", setup_timeout_s=900))
    assert delai_du_setup(declare, 420) == 900
    assert delai_du_setup(PolitiqueRun(worktree=ConfigWorktree(setup="x")), 420) == 420
    assert delai_du_setup(PolitiqueRun(), 420) == 420


async def test_the_runner_receives_the_declared_setup_timeout() -> None:
    _Sequence.resultats = [_OK]
    politique = PolitiqueRun(worktree=ConfigWorktree(setup="x", setup_timeout_s=900))
    preparation = preparation_du_run(
        politique, _WT.racine, _DEPOT, None, delai_du_setup(politique, 420)
    )
    assert preparation is not None
    await preparation()
    assert _Sequence.timeouts == [900]


def _preparation() -> preparation_worktree.Preparation:
    preparation = preparation_du_run(
        PolitiqueRun(worktree=ConfigWorktree(setup="pnpm install")), _WT.racine, _DEPOT, None, 60
    )
    assert preparation is not None
    return preparation


async def test_a_timed_out_setup_is_retried_once_and_the_run_goes_on() -> None:
    _Sequence.resultats = [_DELAI, _OK]
    assert (await _preparation()()).arret is None
    assert _Sequence.appels == 2


async def test_a_setup_with_a_non_zero_exit_code_is_not_retried() -> None:
    _Sequence.resultats = [_CODE_1]
    resultat = await _preparation()()
    assert resultat.arret is not None and resultat.code == 1
    assert _Sequence.appels == 1


async def test_two_timeouts_in_a_row_end_the_run_in_worktree_setup_failed() -> None:
    _Sequence.resultats = [_DELAI, _DELAI]
    evenements: list[OrchestratorEvent] = []
    orch, _ = _orchestrateur([], None)
    orch._preparation = _preparation()  # type: ignore[assignment]
    resultat = await preparer_le_worktree(orch, _run(evenements))
    assert resultat is not None and not resultat.approved
    assert _Sequence.appels == 2
    done = [e for e in evenements if e.type == EventType.PIPELINE_DONE]
    assert [e.data["reason"] for e in done] == ["worktree_setup_failed"]
