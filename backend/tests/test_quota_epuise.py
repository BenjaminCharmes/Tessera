"""A quota exhausted during an agent call is named as such — ticket-498.

Le CLI répond par un `ProcessError` à stderr vide quand l'abonnement est à
sec ; ces tests vérifient que le run le dit, remet le ticket en `todo` et
arrête la file au lieu de compter un échec.
"""
from datetime import datetime, timezone
from pathlib import Path

from claude_agent_sdk import ProcessError

from tessera.models.ticket import TicketStatus
from tessera.services import pipeline_outcomes as outcomes
from tessera.services.pipeline_events import EventType, PipelineResult
from tessera.services.quota_exhaustion import is_quota_exhausted, resume_label
from tessera.services.orchestrator import Orchestrator
from tessera.services.quota_tracker import QuotaSnapshot, QuotaStatus, QuotaTracker
from tests.test_orchestrator import _FakeGit, _make_orchestrator, _make_ticket, _noop
from tests.test_limite_de_session import _Orch, _OrchFile, _collect_events, _run

_EMPTY_STDERR_MSG = "Command failed with exit code 1"
_RESETS_AT = datetime(2026, 10, 17, 7, 38, tzinfo=timezone.utc)


def _snapshot(
    status: QuotaStatus, resets_at: datetime | None = _RESETS_AT
) -> QuotaSnapshot:
    return QuotaSnapshot(
        status=status, utilization=1.0, window="five_hour", resets_at=resets_at
    )


def _process_error() -> ProcessError:
    return ProcessError(_EMPTY_STDERR_MSG, exit_code=1, stderr="")


def test_process_error_with_rejected_snapshot_is_quota_exhausted() -> None:
    assert is_quota_exhausted(_process_error(), _snapshot("rejected")) is True


def test_usage_limit_message_is_quota_exhausted() -> None:
    exc = RuntimeError("Claude AI usage limit reached")

    assert is_quota_exhausted(exc, None) is True
    assert is_quota_exhausted(RuntimeError("Rate Limit hit"), None) is True
    assert is_quota_exhausted(RuntimeError("weekly allowance used"), None) is True


def test_ordinary_process_error_with_allowed_snapshot_is_not_quota() -> None:
    assert is_quota_exhausted(_process_error(), _snapshot("allowed")) is False
    assert is_quota_exhausted(_process_error(), None) is False


def test_empty_stderr_process_error_after_warning_is_quota_exhausted() -> None:
    assert is_quota_exhausted(_process_error(), _snapshot("allowed_warning")) is True


def test_process_error_with_stderr_after_warning_is_not_quota() -> None:
    exc = ProcessError(_EMPTY_STDERR_MSG, exit_code=1, stderr="segfault")

    assert is_quota_exhausted(exc, _snapshot("allowed_warning")) is False


def test_non_process_error_after_warning_is_not_quota() -> None:
    assert is_quota_exhausted(RuntimeError("boom"), _snapshot("allowed_warning")) is False


def test_resume_label_uses_snapshot_reset_time_in_utc() -> None:
    assert resume_label(_snapshot("rejected")) == "07:38 UTC"


def test_resume_label_without_time_is_unknown() -> None:
    assert resume_label(_snapshot("rejected", resets_at=None)) == "heure inconnue"
    assert resume_label(None) == "heure inconnue"


async def test_finish_quota_exhausted_sets_todo_and_logs_resume_time() -> None:
    orch = _Orch()
    run, events = _run()

    result = await outcomes.finish_quota_exhausted(
        orch, run, _process_error(), resume_label(_snapshot("rejected"))
    )

    assert orch._ticket_svc.statut is TicketStatus.todo
    assert result.final_status is TicketStatus.todo
    assert result.approved is False
    assert result.commit_sha == "abc1234"
    ligne = next(line for line in orch.logs if "quota épuisé" in line)
    assert "07:38 UTC" in ligne
    assert "ProcessError" not in ligne
    assert result.arret == "quota_exhausted (reprise : 07:38 UTC)"
    done = [e for e in events if e.type is EventType.PIPELINE_DONE]
    assert done[0].data.get("reason") == "quota_exhausted"


class _OrchQuota(_OrchFile):
    """Comme `_OrchFile`, mais le premier ticket s'arrête sur le quota."""

    async def run_pipeline(  # type: ignore[override]
        self,
        project_id: str,
        ticket_id: str,
        on_event: object,
        run_id: object = None,
        dialogue: object = None,
        envelope_run_id: object = None,
    ) -> PipelineResult:
        self.lances.append(ticket_id)
        return PipelineResult(
            ticket_id=ticket_id,
            final_status=TicketStatus.todo,
            rounds=1,
            approved=False,
            arret="quota_exhausted (reprise : 07:38 UTC)",
        )


async def test_queue_stops_on_quota_exhausted_without_launching_next(
    tmp_path: Path,
) -> None:
    log_path = tmp_path / "memory" / "pipeline-log.md"
    orch = _OrchQuota(log_path=log_path)
    events, on_event = await _collect_events()

    results = await orch.run_queue("proj", ["ticket-001", "ticket-002"], on_event)

    assert orch.lances == ["ticket-001"]
    assert len(results) == 1
    assert results[0].final_status is TicketStatus.todo
    content = log_path.read_text(encoding="utf-8")
    assert "file interrompue : quota épuisé" in content
    assert "limite de session" not in content
    progress = [
        e for e in events
        if e.type is EventType.QUEUE_PROGRESS
        and e.data.get("raison") == "quota_exhausted"
    ]
    assert progress, "un QUEUE_PROGRESS quota_exhausted doit être émis"


class _RunnerQuiEchoue:
    """Runner dont chaque appel d'agent échoue avec l'exception donnée."""

    def __init__(self, exc: BaseException) -> None:
        self._exc = exc

    async def run(self, **kwargs: object) -> None:
        raise self._exc


def _orchestrateur_qui_echoue(
    tmp_path: Path, snapshot: QuotaSnapshot | None
) -> Orchestrator:
    tracker = QuotaTracker()
    tracker.record(snapshot)
    return _make_orchestrator(
        tmp_path,
        runner=_RunnerQuiEchoue(_process_error()),  # type: ignore[arg-type]
        git_workspace=_FakeGit(),
        project_path=tmp_path,
        tickets=[_make_ticket()],
        quota_tracker=tracker,
    )


async def test_pipeline_maps_process_error_after_rejected_snapshot_to_todo(
    tmp_path: Path,
) -> None:
    orch = _orchestrateur_qui_echoue(tmp_path, _snapshot("rejected"))

    result = await orch.run_pipeline("proj", "ticket-001", _noop)

    assert result.final_status is TicketStatus.todo
    assert result.approved is False
    assert result.arret == "quota_exhausted (reprise : 07:38 UTC)"
    log = (tmp_path / "memory" / "pipeline-log.md").read_text(encoding="utf-8")
    assert "quota épuisé" in log
    assert "07:38 UTC" in log


async def test_pipeline_keeps_ordinary_process_error_blocked(tmp_path: Path) -> None:
    orch = _orchestrateur_qui_echoue(tmp_path, _snapshot("allowed"))

    result = await orch.run_pipeline("proj", "ticket-001", _noop)

    assert result.final_status is TicketStatus.blocked
    assert not (result.arret or "").startswith("quota_exhausted")
    log = (tmp_path / "memory" / "pipeline-log.md").read_text(encoding="utf-8")
    assert "quota épuisé" not in log
