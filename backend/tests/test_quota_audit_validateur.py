"""A quota exhausted during the audit or the validation is a quota stop — ticket-505.

Both judges fail closed (ADR-039) and used to turn *any* exception into a
verdict, so an empty subscription read as a refused ticket. A quota error now
travels up to `run_pipeline`; every other failure keeps its closed verdict.
"""
from pathlib import Path
from typing import Any

import pytest

from tessera.models.ticket import TicketStatus
from tessera.services.security_auditor import SecurityAuditorService
from tessera.services.validator import ValidatorService
from tests.test_orchestrator import (
    _FakeGit,
    _make_orchestrator,
    _make_ticket,
    _noop,
    _RecordingRunner,
)
from tests.test_providers_base import FakeProvider

_PROMPTS = Path(__file__).resolve().parents[2] / "agents" / "prompts"
_HIT_LIMIT = "Claude Code returned an error result: You've hit your limit · resets 9pm"
_TURN_LIMIT = "Reached maximum number of turns (20)"
_BODY_WITH_CRITERIA = "## Critères d'acceptation\n\n- [ ] Le comportement attendu existe\n"


class _FailingProvider(FakeProvider):
    """Fails every call with the given error message."""

    def __init__(self, message: str) -> None:
        super().__init__()
        self._message = message

    async def complete(self, **kwargs: Any) -> Any:  # type: ignore[override]
        self.calls.append(kwargs)
        raise RuntimeError(self._message)


# ------------------------------------------------------------------
# Audit
# ------------------------------------------------------------------


async def test_audit_raises_when_the_quota_is_exhausted(tmp_path: Path) -> None:
    service = SecurityAuditorService(_FailingProvider(_HIT_LIMIT), _PROMPTS)

    with pytest.raises(RuntimeError, match="hit your limit"):
        await service.audit("+x = 1", tmp_path)


async def test_audit_diff_only_raises_when_the_quota_is_exhausted(tmp_path: Path) -> None:
    service = SecurityAuditorService(
        _FailingProvider(_TURN_LIMIT),
        _PROMPTS,
        diff_only_provider=_FailingProvider(_HIT_LIMIT),
    )

    with pytest.raises(RuntimeError, match="hit your limit"):
        await service.audit("+x = 1", tmp_path)


async def test_audit_still_blocks_on_any_other_exception(tmp_path: Path) -> None:
    service = SecurityAuditorService(_FailingProvider("provider down"), _PROMPTS)

    result = await service.audit("+x = 1", tmp_path)

    assert result.verdict == "BLOCK"
    assert "provider down" in result.reason


async def test_audit_diff_only_still_blocks_on_any_other_exception(tmp_path: Path) -> None:
    service = SecurityAuditorService(
        _FailingProvider(_TURN_LIMIT),
        _PROMPTS,
        diff_only_provider=_FailingProvider("provider down"),
    )

    result = await service.audit("+x = 1", tmp_path)

    assert result.verdict == "BLOCK"
    assert "provider down" in result.reason


# ------------------------------------------------------------------
# Validateur
# ------------------------------------------------------------------


async def test_validator_raises_when_the_quota_is_exhausted() -> None:
    service = ValidatorService(_FailingProvider(_HIT_LIMIT), _PROMPTS)

    with pytest.raises(RuntimeError, match="hit your limit"):
        await service.validate(["Le comportement attendu existe"], "+x = 1", None)


async def test_validator_still_requests_changes_on_any_other_exception() -> None:
    service = ValidatorService(_FailingProvider("provider down"), _PROMPTS)

    result = await service.validate(["Le comportement attendu existe"], "+x = 1", None)

    assert result.verdict == "CHANGES_REQUESTED"
    assert "provider down" in result.feedback


# ------------------------------------------------------------------
# Orchestrateur
# ------------------------------------------------------------------


def _journal(tmp_path: Path) -> str:
    return (tmp_path / "memory" / "pipeline-log.md").read_text(encoding="utf-8")


async def test_quota_exhausted_during_audit_stops_the_run_as_a_quota_stop(
    tmp_path: Path,
) -> None:
    git = _FakeGit()
    orch = _make_orchestrator(
        tmp_path,
        runner=_RecordingRunner(),  # type: ignore[arg-type]
        git_workspace=git,
        security_auditor=SecurityAuditorService(_FailingProvider(_HIT_LIMIT), _PROMPTS),
        project_path=tmp_path,
        tickets=[_make_ticket()],
    )

    result = await orch.run_pipeline("proj", "ticket-001", _noop)

    assert result.final_status is TicketStatus.todo
    assert result.approved is False
    assert (result.arret or "").startswith("quota_exhausted")
    journal = _journal(tmp_path)
    assert "quota épuisé" in journal
    assert "securite: BLOCK" not in journal
    assert len(git.commits) == 1


async def test_other_audit_failure_still_blocks_the_ticket(tmp_path: Path) -> None:
    orch = _make_orchestrator(
        tmp_path,
        runner=_RecordingRunner(),  # type: ignore[arg-type]
        git_workspace=_FakeGit(),
        security_auditor=SecurityAuditorService(_FailingProvider("provider down"), _PROMPTS),
        project_path=tmp_path,
        tickets=[_make_ticket()],
    )

    result = await orch.run_pipeline("proj", "ticket-001", _noop)

    assert result.final_status is TicketStatus.blocked
    assert not (result.arret or "").startswith("quota_exhausted")
    assert "quota épuisé" not in _journal(tmp_path)


async def test_quota_exhausted_during_validation_stops_the_run_as_a_quota_stop(
    tmp_path: Path,
) -> None:
    orch = _make_orchestrator(
        tmp_path,
        runner=_RecordingRunner(),  # type: ignore[arg-type]
        git_workspace=_FakeGit(),
        validator=ValidatorService(_FailingProvider(_HIT_LIMIT), _PROMPTS),
        project_path=tmp_path,
        tickets=[_make_ticket(body=_BODY_WITH_CRITERIA)],
    )

    result = await orch.run_pipeline("proj", "ticket-001", _noop)

    assert result.final_status is TicketStatus.todo
    assert result.approved is False
    assert (result.arret or "").startswith("quota_exhausted")
    assert "quota épuisé" in _journal(tmp_path)
