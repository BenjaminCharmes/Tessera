"""Light tickets defer documentation to the next normal run — ticket-292.

Un ticket déclaré `light: true` :
- fait parser `ticket.light == True` depuis le frontmatter
- saute la mise à jour de la documentation sur son run approuvé
- ne supprime pas l'audit sécurité ni la validation
- est couvert par la documentation du prochain ticket normal
"""
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import frontmatter
import pytest

from tessera.models.agent import AgentResult, AgentRole
from tessera.services.documentation import ResultatDocumentation
from tessera.services.pipeline_events import EventType, OrchestratorEvent
from tessera.services.security_auditor import SecurityAuditResult
from tessera.services.ticket_service import TicketService
from tessera.services.validator import ValidationResult
from tests.test_orchestrator import (
    _FakeGit,
    _make_agent_result,
    _make_orchestrator,
    _make_ticket,
    _noop,
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _write_ticket(path: Path, **extra: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    post = frontmatter.Post(
        content="Corps du ticket.",
        id="ticket-001",
        title="Test",
        type="chore",
        status="todo",
        priority="medium",
        agent="codeur",
        created="2026-10-02",
        **extra,
    )
    path.write_text(frontmatter.dumps(post), encoding="utf-8")


def _svc_light(light: bool) -> AsyncMock:
    """Ticket service double returning a ticket with the given light value."""
    ticket = _make_ticket(light=light)
    svc = AsyncMock()
    svc.get_ticket.return_value = ticket
    svc.update_status.return_value = ticket
    return svc


def _runner_approuve() -> MagicMock:
    """Runner double that always approves."""
    async def fake_run(**kwargs: object) -> AgentResult:
        role = kwargs["role"]
        content = "APPROVED" if role == AgentRole.reviewer else "fait"
        return _make_agent_result(content, role=role)  # type: ignore[arg-type]

    r = MagicMock()
    r.run = fake_run
    return r


def _documenteur(fichiers: list[str] | None = None) -> AsyncMock:
    return AsyncMock(
        return_value=ResultatDocumentation(fichiers or [], [], ["ticket-001"])
    )


# ------------------------------------------------------------------
# Parsing du frontmatter
# ------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, attendu",
    [
        (True, True),
        (False, False),
        (None, False),
        ("yes", False),
        (1, False),
    ],
)
async def test_light_parsed_from_frontmatter(
    tmp_path: Path, raw: object, attendu: bool
) -> None:
    """Only a YAML boolean `true` activates light."""
    path = tmp_path / "tickets" / "todo" / "ticket-001-slug.md"
    if raw is None:
        _write_ticket(path)
    else:
        _write_ticket(path, light=raw)

    ticket = await TicketService(tmp_path, "p").get_ticket("ticket-001")

    assert ticket is not None
    assert ticket.light is attendu


# ------------------------------------------------------------------
# Documentation skippée sur un run léger
# ------------------------------------------------------------------


async def test_approved_light_ticket_skips_documenter(tmp_path: Path) -> None:
    """An approved light ticket must not call the documenter."""
    documenter = _documenteur(["README.md"])
    orc = _make_orchestrator(
        tmp_path,
        runner=_runner_approuve(),
        ticket_service=_svc_light(light=True),
        git_workspace=_FakeGit(),
    )
    orc._documenter = documenter

    await orc.run_pipeline("proj", "ticket-001", _noop)

    documenter.assert_not_awaited()


async def test_approved_light_ticket_emits_no_documentation_started(
    tmp_path: Path,
) -> None:
    """No DOCUMENTATION_STARTED event is emitted for a light ticket."""
    events: list[OrchestratorEvent] = []

    async def capture(ev: OrchestratorEvent) -> None:
        events.append(ev)

    orc = _make_orchestrator(
        tmp_path,
        runner=_runner_approuve(),
        ticket_service=_svc_light(light=True),
        git_workspace=_FakeGit(),
    )
    orc._documenter = _documenteur(["README.md"])

    await orc.run_pipeline("proj", "ticket-001", capture)

    doc_events = [e for e in events if e.type is EventType.DOCUMENTATION_STARTED]
    assert not doc_events


async def test_non_light_ticket_still_documents(tmp_path: Path) -> None:
    """Normal (non-light) tickets keep triggering the documenter."""
    documenter = _documenteur(["README.md"])
    orc = _make_orchestrator(
        tmp_path,
        runner=_runner_approuve(),
        ticket_service=_svc_light(light=False),
        git_workspace=_FakeGit(),
    )
    orc._documenter = documenter

    await orc.run_pipeline("proj", "ticket-001", _noop)

    documenter.assert_awaited_once()


# ------------------------------------------------------------------
# Sécurité et validation non allégées
# ------------------------------------------------------------------


async def test_light_ticket_runs_security_audit(tmp_path: Path) -> None:
    """A light ticket must still go through the security audit."""
    audits: list[str] = []

    class _FakeAuditor:
        async def audit(self, code_diff: str, project_path: Path) -> object:
            audits.append(code_diff)
            return SecurityAuditResult(verdict="PASS", issues=[], summary="ok")

    orc = _make_orchestrator(
        tmp_path,
        runner=_runner_approuve(),
        ticket_service=_svc_light(light=True),
        git_workspace=_FakeGit(),
        security_auditor=_FakeAuditor(),
        project_path=tmp_path,
    )

    await orc.run_pipeline("proj", "ticket-001", _noop)

    assert audits, "security audit was not called for a light ticket"


async def test_light_ticket_runs_validator(tmp_path: Path) -> None:
    """A light ticket must still go through the validator."""
    validated: list[object] = []

    class _FakeValidator:
        async def validate(
            self,
            criteria: list[str],
            code_produced: str,
            test_result: object,
        ) -> object:
            validated.append(code_produced)
            return ValidationResult(
                all_passed=True, criteria=[], verdict="APPROVED", feedback=""
            )

    orc = _make_orchestrator(
        tmp_path,
        runner=_runner_approuve(),
        ticket_service=_svc_light(light=True),
        git_workspace=_FakeGit(),
        validator=_FakeValidator(),
        project_path=tmp_path,
    )

    await orc.run_pipeline("proj", "ticket-001", _noop)

    assert validated, "validator was not called for a light ticket"


# ------------------------------------------------------------------
# Le run suivant non léger documente le lot entier
# ------------------------------------------------------------------


async def test_next_non_light_run_documents_the_batch(tmp_path: Path) -> None:
    """After a skipped light run, the next normal run triggers the documenter.

    Le marqueur n'avance pas sur le run léger, donc le prochain run normal
    documente le lot depuis le marqueur — léger inclus.
    """
    documenter = _documenteur(["README.md"])

    # Premier run : ticket léger — le documenteur ne doit pas être appelé.
    orc_light = _make_orchestrator(
        tmp_path,
        runner=_runner_approuve(),
        ticket_service=_svc_light(light=True),
        git_workspace=_FakeGit(),
    )
    orc_light._documenter = documenter
    await orc_light.run_pipeline("proj", "ticket-001", _noop)
    assert documenter.await_count == 0, "documenter called on a light run"

    # Deuxième run : ticket normal — le documenteur doit être appelé.
    svc_normal = _svc_light(light=False)
    svc_normal.get_ticket.return_value = _make_ticket(id="ticket-002", light=False)
    svc_normal.update_status.return_value = _make_ticket(id="ticket-002", light=False)

    orc_normal = _make_orchestrator(
        tmp_path,
        runner=_runner_approuve(),
        ticket_service=svc_normal,
        git_workspace=_FakeGit(),
    )
    orc_normal._documenter = documenter
    await orc_normal.run_pipeline("proj", "ticket-002", _noop)
    assert documenter.await_count == 1, "documenter not called on the following normal run"
