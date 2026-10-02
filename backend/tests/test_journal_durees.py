"""Duration is logged for each pipeline stage — ticket-288.

Covers:
- Security audit log line contains duration in milliseconds.
- Validation log line contains duration in milliseconds.
- Documentation success: log line with duration and file count.
- Documentation failure: log line with failure reason.
- Livraison: one log line per step with duration, including CI wait.
- CHANGES_REQUESTED log uses raw verdict when reviewer gives no structured reason.
"""
from pathlib import Path
from unittest.mock import AsyncMock, patch

from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services import pipeline_stages as stages
from tessera.services.livraison import Livraison
from tessera.services.orchestrator import Orchestrator
from tessera.services.pipeline_events import EventType, OrchestratorEvent, PipelineResult
from tessera.services.pipeline_run import PipelineRun
from tessera.services.security_auditor import SecurityAuditResult
from tessera.services.validator import ValidationResult


# ------------------------------------------------------------------
# Helpers partagés
# ------------------------------------------------------------------


def _ticket(**kwargs: object) -> Ticket:
    base: dict[str, object] = dict(
        id="ticket-001",
        title="Test feature",
        type=TicketType.feat,
        status=TicketStatus.todo,
        priority=TicketPriority.medium,
        agent="codeur",
        body="## Critères d'acceptation\n- [ ] ça marche\n",
    )
    base.update(kwargs)
    return Ticket(**base)  # type: ignore[arg-type]


class _OrchStub:
    """Orchestrateur minimal qui collecte les lignes de journal."""

    def __init__(self, **attrs: object) -> None:
        self._git_workspace = None
        self._project_context = "contexte"
        self._test_runner = None
        self._project_path = None
        self._test_command = None
        self._security_auditor = None
        self._validator = None
        self.logs: list[str] = []
        for k, v in attrs.items():
            setattr(self, k, v)

    def _log(self, message: str) -> None:
        self.logs.append(message)


def _run(events: list[OrchestratorEvent] | None = None) -> PipelineRun:
    collected = events if events is not None else []

    async def _on_event(event: OrchestratorEvent) -> None:
        collected.append(event)

    return PipelineRun(project_id="proj", ticket=_ticket(), on_event=_on_event)


def _build_orch(tmp_path: Path, **kwargs: object) -> Orchestrator:
    """Crée un Orchestrator réel avec les chemins de test."""
    log_path = tmp_path / "memory" / "log.md"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    ticket_svc = AsyncMock()
    ticket_svc.update_status = AsyncMock()
    return Orchestrator(
        runner=AsyncMock(),
        ticket_service=ticket_svc,
        project_context="ctx",
        agent_configs=[],
        pipeline_log_path=log_path,
        **kwargs,  # type: ignore[arg-type]
    )


def _resultat(ticket_id: str = "ticket-001", approved: bool = True) -> PipelineResult:
    return PipelineResult(
        ticket_id=ticket_id,
        final_status=TicketStatus.done if approved else TicketStatus.blocked,
        rounds=1,
        approved=approved,
        branch=f"{ticket_id}-slug",
    )


# ------------------------------------------------------------------
# Audit sécurité — durée dans le journal
# ------------------------------------------------------------------


class _AuditeurInstant:
    async def audit(self, code_diff: str, project_path: Path) -> SecurityAuditResult:
        return SecurityAuditResult(
            issues=[],
            verdict="PASS",
            summary="Aucune vulnérabilité.",
            reason="",
        )


async def test_security_audit_log_contient_la_duree() -> None:
    """The security audit log line carries the duration in milliseconds."""
    orch = _OrchStub(
        _security_auditor=_AuditeurInstant(),
        _project_path=Path("."),
        _ticket_svc=type("T", (), {"update_status": AsyncMock()})(),
    )
    run = _run()
    run.reviewed_code = "diff"

    await stages.run_security_audit(orch, run)  # type: ignore[arg-type]

    assert orch.logs, "security audit should write at least one log line"
    line = orch.logs[-1]
    assert "securite" in line
    assert "ms)" in line, f"duration suffix not found in: {line!r}"


# ------------------------------------------------------------------
# Validateur — durée dans le journal
# ------------------------------------------------------------------


class _ValidateurInstant:
    async def validate(self, **kwargs: object) -> ValidationResult:
        return ValidationResult(
            verdict="APPROVED",
            all_passed=True,
            feedback="tout est bon",
            criteria=[],
        )


async def test_validation_log_contient_la_duree() -> None:
    """The validation log line carries the duration in milliseconds."""
    orch = _OrchStub(_validator=_ValidateurInstant())
    run = _run()

    await stages.run_validation(orch, run)  # type: ignore[arg-type]

    assert orch.logs, "validation should write at least one log line"
    line = orch.logs[-1]
    assert "validateur" in line
    assert "ms)" in line, f"duration suffix not found in: {line!r}"


# ------------------------------------------------------------------
# Documentation — durée et nombre de fichiers (succès) ; ligne d'échec
# ------------------------------------------------------------------


async def test_documentation_reussie_log_duree_et_nombre_de_fichiers(
    tmp_path: Path,
) -> None:
    """A successful documentation run logs its duration and file count."""

    class _DocOK:
        fichiers_modifies = ["docs/guide.md", "docs/api.md"]
        refus: list[str] = []
        tickets: list[str] = []
        tronque = False
        marqueur_ecrit = False

    async def _documenter() -> _DocOK:
        return _DocOK()

    orch = _build_orch(tmp_path, documenter=_documenter)
    events: list[OrchestratorEvent] = []

    async def _on_event(e: OrchestratorEvent) -> None:
        events.append(e)

    await orch._documenter_le_run(_resultat(), _on_event)

    log_content = (tmp_path / "memory" / "log.md").read_text(encoding="utf-8")
    assert "documentation" in log_content, "no documentation log entry"
    assert "2" in log_content, "file count (2) not found in log"
    assert "ms)" in log_content, f"duration not found in log: {log_content!r}"


async def test_documentation_echouee_log_echec(tmp_path: Path) -> None:
    """A failed documentation run logs a failure line."""

    async def _documenter_en_panne() -> None:
        raise RuntimeError("provider down")

    orch = _build_orch(tmp_path, documenter=_documenter_en_panne)
    events: list[OrchestratorEvent] = []

    async def _on_event(e: OrchestratorEvent) -> None:
        events.append(e)

    await orch._documenter_le_run(_resultat(), _on_event)

    log_content = (tmp_path / "memory" / "log.md").read_text(encoding="utf-8")
    assert "documentation" in log_content, "no documentation log entry"
    assert "échec" in log_content, f"failure marker not found in log: {log_content!r}"


# ------------------------------------------------------------------
# Livraison — une ligne par étape avec durée, dont l'attente CI
# ------------------------------------------------------------------


async def test_livraison_log_une_ligne_par_etape_avec_duree(tmp_path: Path) -> None:
    """Livraison logs one line per step with its duration; CI wait gets its own line."""

    async def _livrer(r: PipelineResult) -> Livraison:
        return Livraison(
            etapes=(
                "rebase sur develop",
                "PR #7 ouverte",
                "CI : passing",
                "PR #7 mergée",
            ),
            durees_ms=(120.0, 350.0, 8500.0, 200.0),
            pr_number=7,
            merged=True,
        )

    class _OrchLivraison(Orchestrator):
        async def _run_enregistre(self, *args: object, **kwargs: object) -> PipelineResult:  # type: ignore[override]
            return _resultat()

    log_path = tmp_path / "memory" / "log.md"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    ticket_svc = AsyncMock()
    ticket_svc.update_status = AsyncMock()
    orch = _OrchLivraison(
        runner=AsyncMock(),
        ticket_service=ticket_svc,
        project_context="ctx",
        agent_configs=[],
        pipeline_log_path=log_path,
        livrer=_livrer,
    )

    events: list[OrchestratorEvent] = []

    async def _on_event(e: OrchestratorEvent) -> None:
        events.append(e)

    await orch.run_pipeline("proj", "ticket-001", _on_event)

    log_content = log_path.read_text(encoding="utf-8")
    livraison_lines = [l for l in log_content.splitlines() if "livraison:" in l]
    assert len(livraison_lines) == 4, (
        f"expected 4 livraison log lines, got {len(livraison_lines)}: {livraison_lines}"
    )
    ci_line = next((l for l in livraison_lines if "CI" in l), None)
    assert ci_line is not None, "no CI step log line"
    assert "8500ms" in ci_line, f"CI duration not found in: {ci_line!r}"


# ------------------------------------------------------------------
# CHANGES_REQUESTED — reprend le verdict brut quand il n'y a pas de motif
# ------------------------------------------------------------------


async def test_changes_requested_log_reprend_le_verdict_brut(tmp_path: Path) -> None:
    """When the reviewer gives no structured reason, the log uses the raw verdict."""
    raw_verdict = "Ce code ne respecte pas les conventions du projet."

    orch = _build_orch(tmp_path, max_review_rounds=1)
    run = _run()

    with (
        patch.object(stages, "run_coder", new=AsyncMock()),
        patch.object(stages, "run_tests", new=AsyncMock(return_value=True)),
        patch.object(stages, "run_security_audit", new=AsyncMock(return_value=None)),
        patch.object(
            stages, "run_review", new=AsyncMock(return_value=(False, "", raw_verdict))
        ),
    ):
        await orch._run_rounds(run, "ticket-001")

    log_content = (tmp_path / "memory" / "log.md").read_text(encoding="utf-8")
    assert "CHANGES_REQUESTED" in log_content
    assert raw_verdict[:50] in log_content, (
        f"raw verdict not found in log: {log_content!r}"
    )
