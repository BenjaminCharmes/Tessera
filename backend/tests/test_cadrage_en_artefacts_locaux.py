"""Design tickets on local-artifact projects — ticket-274.

Tests the four acceptance criteria:
1. On ``artifacts: local``, a decision added to memory/decisions.md during the
   run appears in the material transmitted to the validator.
2. A ticket created in tickets/todo/ during the run appears there too.
3. On ``artifacts: tracked``, a ticket created during a design run appears in
   the validator material, even though tickets/ is excluded from the git diff.
4. No file from memory/ or tickets/ is committed on an ``artifacts: local``
   project.
"""
import asyncio
from pathlib import Path
from dataclasses import dataclass

import pytest

from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services import pipeline_stages as stages
from tessera.services.artifact_snapshot import diff_artifacts, snapshot_artifacts
from tessera.services.pipeline_events import OrchestratorEvent
from tessera.services.pipeline_run import PipelineRun
from tessera.services.validator import CriterionResult, ValidationResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ticket(**kwargs: object) -> Ticket:
    base = dict(
        id="ticket-001",
        title="Plan de développement",
        type=TicketType.design,
        status=TicketStatus.todo,
        priority=TicketPriority.medium,
        agent="architect",
        body="## Critères d'acceptation\n- [ ] Décisions documentées\n",
    )
    base.update(kwargs)
    return Ticket(**base)  # type: ignore[arg-type]


def _run(project_path: Path | None = None) -> PipelineRun:
    async def _noop(event: OrchestratorEvent) -> None:
        pass

    run = PipelineRun(project_id="projet", ticket=_ticket(), on_event=_noop)
    if project_path is not None and project_path.is_dir():
        run.artifact_snapshot = snapshot_artifacts(project_path)
    return run


@dataclass
class _FakeValidation:
    """What the mock validator captures from each call."""
    code_produced: str


class _MockValidator:
    """Captures code_produced; always approves."""

    def __init__(self) -> None:
        self.calls: list[_FakeValidation] = []

    async def validate(
        self,
        criteria: list[str],
        code_produced: str,
        test_result: object,
        project_root: object = None,
    ) -> ValidationResult:
        self.calls.append(_FakeValidation(code_produced=code_produced))
        return ValidationResult(
            all_passed=True,
            criteria=[
                CriterionResult(criterion=c, passed=True) for c in criteria
            ],
            verdict="APPROVED",
            feedback="ok",
        )


class _Orch:
    """Minimal orchestrator — only the attributes read by run_validation."""

    def __init__(self, validator: _MockValidator, project_path: Path | None = None) -> None:
        self._validator = validator
        self._project_path = project_path

    def _log(self, message: str) -> None:  # noqa: ARG002
        pass  # captured logs are not needed in these tests


# ---------------------------------------------------------------------------
# Criterion 1 — decision in memory/ reaches the validator (local mode)
# ---------------------------------------------------------------------------


async def test_decision_en_local_figure_dans_le_materiau_du_validateur(
    tmp_path: Path,
) -> None:
    """A decision written to memory/decisions.md reaches the validator (local mode)."""
    project = tmp_path / "projet"
    project.mkdir()
    (project / "memory").mkdir()

    run = _run(project)

    # Architect writes a decision after the snapshot was taken.
    (project / "memory" / "decisions.md").write_text(
        "# Décisions\n## ADR-001 — Décision importante\nTexte de la décision.\n",
        encoding="utf-8",
    )

    # Simulate what _capture_artifact_diff does.
    assert run.artifact_snapshot is not None
    run.artifact_diff = diff_artifacts(run.artifact_snapshot, project)

    validator = _MockValidator()
    orch = _Orch(validator=validator, project_path=project)

    approved, _ = await stages.run_validation(orch, run)  # type: ignore[arg-type]

    assert approved
    assert validator.calls, "le validateur doit être appelé"
    code_produced = validator.calls[0].code_produced
    assert "ADR-001" in code_produced
    assert "Décision importante" in code_produced


# ---------------------------------------------------------------------------
# Criterion 2 — ticket in tickets/todo/ reaches the validator
# ---------------------------------------------------------------------------


async def test_ticket_cree_figure_dans_le_materiau_du_validateur(
    tmp_path: Path,
) -> None:
    """A ticket file created in tickets/todo/ reaches the validator."""
    project = tmp_path / "projet"
    project.mkdir()
    (project / "tickets" / "todo").mkdir(parents=True)

    run = _run(project)

    # Architect creates a ticket after the snapshot was taken.
    (project / "tickets" / "todo" / "ticket-002-ma-feature.md").write_text(
        "# ticket-002\nObjectif: implémenter la feature X.\n",
        encoding="utf-8",
    )

    assert run.artifact_snapshot is not None
    run.artifact_diff = diff_artifacts(run.artifact_snapshot, project)

    validator = _MockValidator()
    orch = _Orch(validator=validator, project_path=project)

    approved, _ = await stages.run_validation(orch, run)  # type: ignore[arg-type]

    assert approved
    assert validator.calls
    code_produced = validator.calls[0].code_produced
    assert "ticket-002" in code_produced
    assert "implémenter la feature X" in code_produced


# ---------------------------------------------------------------------------
# Criterion 3 — tracked project: ticket in tickets/ still reaches validator
# ---------------------------------------------------------------------------


async def test_ticket_tracked_figure_dans_le_materiau_du_validateur(
    tmp_path: Path,
) -> None:
    """On a tracked-artifact project, a new ticket still reaches the validator.

    tickets/ is excluded from the git diff by _ORCHESTRATOR_ARTIFACT_PATHS,
    so a design run that only creates tickets would hand an empty git diff to
    the validator.  The artifact diff bridges that gap regardless of artifact
    mode.
    """
    project = tmp_path / "projet"
    project.mkdir()
    (project / "tickets" / "todo").mkdir(parents=True)
    # Pre-existing ticket (already in snapshot)
    (project / "tickets" / "todo" / "ticket-001-existant.md").write_text(
        "# ticket-001\nexistant\n",
        encoding="utf-8",
    )

    run = _run(project)

    # Architect creates a new ticket after snapshot.
    (project / "tickets" / "todo" / "ticket-003-nouveau.md").write_text(
        "# ticket-003\nObjectif: nouvelle feature Y.\n",
        encoding="utf-8",
    )

    assert run.artifact_snapshot is not None
    run.artifact_diff = diff_artifacts(run.artifact_snapshot, project)

    validator = _MockValidator()
    orch = _Orch(validator=validator, project_path=project)

    # Simulate no git diff (as on a tracked project where tickets/ is excluded)
    run.reviewed_code = ""

    approved, _ = await stages.run_validation(orch, run)  # type: ignore[arg-type]

    assert approved
    assert validator.calls
    code_produced = validator.calls[0].code_produced
    # The pre-existing ticket must NOT appear (unchanged).
    assert "ticket-001-existant" not in code_produced
    # The new ticket MUST appear.
    assert "ticket-003" in code_produced
    assert "nouvelle feature Y" in code_produced


# ---------------------------------------------------------------------------
# Criterion 4 — no memory/ or tickets/ file is committed on local mode
# ---------------------------------------------------------------------------


async def _git(cwd: Path, *args: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "git", *args, cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    assert proc.returncode == 0, err.decode()
    return out.decode()


@pytest.fixture
async def projet_local_avec_artefacts(tmp_path: Path) -> Path:
    """Project in local-artifact mode with memory/ and tickets/ excluded."""
    p = tmp_path / "projet"
    p.mkdir()
    await _git(p, "init", "-q", "-b", "main")
    await _git(p, "config", "user.email", "t@t.local")
    await _git(p, "config", "user.name", "t")
    (p / "app.py").write_text("x = 1\n", encoding="utf-8")
    await _git(p, "add", "app.py")
    await _git(p, "commit", "-qm", "init")

    # Local-artifact mode: exclude from git
    (p / ".git" / "info").mkdir(parents=True, exist_ok=True)
    (p / ".git" / "info" / "exclude").write_text(
        "tickets/\nmemory/\nCLAUDE.md\nagents.json\n", encoding="utf-8"
    )
    (p / "tickets" / "todo").mkdir(parents=True)
    (p / "memory").mkdir()
    return p


async def test_artefacts_locaux_non_commites_sur_mode_local(
    projet_local_avec_artefacts: Path,
) -> None:
    """memory/ and tickets/ files are not committed on a local-artifact project."""
    from tessera.services.git_workspace import GitWorkspaceService

    project = projet_local_avec_artefacts

    # Snapshot before the architect writes anything.
    before = snapshot_artifacts(project)

    svc = GitWorkspaceService(project)
    await svc.create_branch("ticket-001", "cadrage")

    # Architect writes to artifact directories.
    (project / "memory" / "decisions.md").write_text(
        "## ADR-001\nDécision.\n", encoding="utf-8"
    )
    (project / "tickets" / "todo" / "ticket-002.md").write_text(
        "# ticket-002\nObjectif.\n", encoding="utf-8"
    )
    # Coder also produces a code file (this should be committed).
    (project / "app.py").write_text("x = 2\n", encoding="utf-8")

    # Verify artifact diff captured the changes.
    artifact_diff = diff_artifacts(before, project)
    assert "ADR-001" in artifact_diff
    assert "ticket-002" in artifact_diff

    # Commit (as the pipeline does at end of run).
    sha = await svc.commit_all("feat: ticket-001 — cadrage")

    # Code change is committed.
    assert sha is not None, "le travail du codeur doit être commité"

    # Artifact directories are not in git history.
    tracked = await _git(project, "ls-files")
    assert "memory/decisions.md" not in tracked
    assert "tickets/todo/ticket-002.md" not in tracked
    assert "app.py" in tracked

    # artifact_diff is text in memory, not in any commit.
    log = await _git(project, "log", "--format=%s")
    assert "ADR-001" not in log
    assert "Décision" not in log
