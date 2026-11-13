"""A round whose real diff is empty is never approved (ticket-960)."""

from pathlib import Path

from tessera.models.agent import AgentResult, AgentRole
from tessera.services.pipeline.orchestrator import Orchestrator
from tests.test_orchestrator import DIFF_REEL, _FailingDiffGit, _FakeGit, _make_orchestrator, _noop, _RecordingRunner


def _coder_prompts(runner: _RecordingRunner) -> list[str]:
    return [
        str(c["project_context"]) for c in runner.calls if c["role"] == AgentRole.codeur
    ]


async def _run(orchestrator: Orchestrator) -> bool:
    result = await orchestrator.run_pipeline("projet", "ticket-001", _noop)
    return result.approved


async def test_empty_diff_with_two_approvals_is_not_approved(tmp_path: Path) -> None:
    runner = _RecordingRunner()
    orchestrator = _make_orchestrator(
        tmp_path, runner=runner, git_workspace=_FakeGit(diff=""), project_path=tmp_path
    )

    assert await _run(orchestrator) is False
    # Le retour du tour 1 atteint le codeur au tour 2.
    prompts = _coder_prompts(runner)
    assert len(prompts) > 1
    assert "aucun fichier modifié" in prompts[1].lower()


async def test_non_empty_diff_with_two_approvals_is_approved(tmp_path: Path) -> None:
    orchestrator = _make_orchestrator(
        tmp_path,
        runner=_RecordingRunner(),
        git_workspace=_FakeGit(diff=DIFF_REEL),
        project_path=tmp_path,
    )

    assert await _run(orchestrator) is True


async def test_diff_failure_prevents_approval(tmp_path: Path) -> None:
    orchestrator = _make_orchestrator(
        tmp_path,
        runner=_RecordingRunner(),
        git_workspace=_FailingDiffGit(),
        project_path=tmp_path,
    )

    assert await _run(orchestrator) is False


class _ArtifactWritingRunner(_RecordingRunner):
    """Producer that writes only an artifact, like an architect on a design run."""

    def __init__(self, projet: Path) -> None:
        super().__init__()
        self._projet = projet

    async def run(self, **kwargs: object) -> AgentResult:
        if kwargs["role"] in (AgentRole.codeur, AgentRole.architect):
            decisions = self._projet / "memory" / "decisions.md"
            decisions.parent.mkdir(parents=True, exist_ok=True)
            decisions.write_text("## ADR-999\n", encoding="utf-8")
        return await super().run(**kwargs)


async def test_empty_git_diff_with_an_artifact_change_is_approved(tmp_path: Path) -> None:
    orchestrator = _make_orchestrator(
        tmp_path,
        runner=_ArtifactWritingRunner(tmp_path),
        git_workspace=_FakeGit(diff=""),
        project_path=tmp_path,
    )

    assert await _run(orchestrator) is True


async def test_without_git_workspace_a_double_approval_stays_approved(
    tmp_path: Path,
) -> None:
    orchestrator = _make_orchestrator(
        tmp_path, runner=_RecordingRunner(), git_workspace=None, project_path=tmp_path
    )

    assert await _run(orchestrator) is True
