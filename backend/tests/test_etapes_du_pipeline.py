"""Each pipeline stage announces its start — ticket-255.

Covers:
- `validation_started` emitted before `validation_done` when a validator is
  active; absent when there is none.
- `documentation_started` emitted before `doc_updated` on an approved run with
  a documenter.
- `livraison_started` emitted before `livraison_done` on an approved run;
  absent on a non-approved run.
- `RunActif.en_dict()` exposes `etape`, and `_suivre` sets it to `"validation"`
  on `validation_started`.
"""
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from tessera.models.agent import AgentResult, AgentRole
from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services import pipeline_stages as stages
from tessera.services.livraison import Livraison
from tessera.services.orchestrator import Orchestrator
from tessera.services.pipeline_events import EventType, OrchestratorEvent, PipelineResult
from tessera.services.pipeline_run import PipelineRun
from tessera.services.run_executor import _suivre
from tessera.services.run_registry import RunActif
from tessera.services.validator import CriterionResult, ValidationResult


# ------------------------------------------------------------------
# Shared test doubles
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


class _Orch:
    """Orchestrateur minimal pour les étapes testées isolément."""

    def __init__(self, **attrs: object) -> None:
        self._git_workspace = None
        self._project_context = "contexte"
        self._test_runner = None
        self._project_path = None
        self._test_command = None
        self._security_auditor = None
        self._validator = None
        for k, v in attrs.items():
            setattr(self, k, v)

    def _log(self, message: str) -> None:
        pass


def _run(events: list[OrchestratorEvent] | None = None) -> PipelineRun:
    collected = events if events is not None else []

    async def _on_event(event: OrchestratorEvent) -> None:
        collected.append(event)

    return PipelineRun(project_id="proj", ticket=_ticket(), on_event=_on_event)


class _ValidateurOK:
    async def validate(self, **kwargs: object) -> ValidationResult:
        return ValidationResult(
            verdict="APPROVED",
            all_passed=True,
            feedback="ok",
            criteria=[CriterionResult(criterion="ça marche", passed=True, note="")],
        )


# ------------------------------------------------------------------
# validation_started
# ------------------------------------------------------------------


async def test_validation_started_emis_avant_validation_done_avec_validateur() -> None:
    # Sans cet événement, plusieurs minutes de silence entre `reviewer terminé`
    # et `validation_done` laissaient l'écran figé (ticket-255).
    events: list[OrchestratorEvent] = []
    run = _run(events)
    orch = _Orch(_validator=_ValidateurOK())

    await stages.run_validation(orch, run, "")

    types = [e.type for e in events]
    assert EventType.VALIDATION_STARTED in types, "validation_started absent"
    assert EventType.VALIDATION_DONE in types, "validation_done absent"
    assert types.index(EventType.VALIDATION_STARTED) < types.index(
        EventType.VALIDATION_DONE
    ), "validation_started doit précéder validation_done"


async def test_validation_started_non_emis_sans_validateur() -> None:
    # Un run sans validateur ne doit pas annoncer une étape qui n'a pas lieu.
    events: list[OrchestratorEvent] = []
    run = _run(events)
    orch = _Orch()  # _validator = None

    await stages.run_validation(orch, run, "")

    assert EventType.VALIDATION_STARTED not in [e.type for e in events]


# ------------------------------------------------------------------
# documentation_started
# ------------------------------------------------------------------


def _make_orchestrator(tmp_path: Path, **kwargs: object) -> Orchestrator:
    from tests.test_orchestrator import _make_orchestrator as _mo

    return _mo(tmp_path, **kwargs)


def _coder_runner(approuve: bool = True) -> Any:
    async def fake_run(**kwargs: Any) -> AgentResult:
        from tests.test_orchestrator import _make_agent_result

        role = kwargs["role"]
        verdict = "APPROVED" if approuve else "CHANGES_REQUESTED: non"
        content = verdict if role == AgentRole.reviewer else "code produit"
        return _make_agent_result(content, role)

    r = MagicMock()
    r.run = fake_run
    return r


async def test_documentation_started_emis_avant_doc_updated(tmp_path: Path) -> None:
    from tessera.services.documentation import ResultatDocumentation
    from tests.test_orchestrator import _FakeGit

    documenter = AsyncMock(
        return_value=ResultatDocumentation(["README.md"], [], ["ticket-001"])
    )
    orc = _make_orchestrator(tmp_path, runner=_coder_runner(), git_workspace=_FakeGit())
    orc._documenter = documenter

    events: list[OrchestratorEvent] = []

    async def capture(ev: OrchestratorEvent) -> None:
        events.append(ev)

    await orc.run_pipeline("proj", "ticket-001", capture)

    types = [e.type for e in events]
    assert EventType.DOCUMENTATION_STARTED in types, "documentation_started absent"
    assert EventType.DOC_UPDATED in types, "doc_updated absent"
    assert types.index(EventType.DOCUMENTATION_STARTED) < types.index(
        EventType.DOC_UPDATED
    ), "documentation_started doit précéder doc_updated"


# ------------------------------------------------------------------
# livraison_started
# ------------------------------------------------------------------


class _OrchDouble(Orchestrator):
    """Orchestrateur dont seul `_run_pipeline` est remplacé par un résultat fixe."""

    def __init__(self, resultat: PipelineResult, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._resultat_fixe = resultat

    async def _run_pipeline(self, *args: Any, **kwargs: Any) -> PipelineResult:
        return self._resultat_fixe


def _construire_double(tmp_path: Path, resultat: PipelineResult, livrer: Any) -> _OrchDouble:
    tickets = AsyncMock()
    tickets.get_ticket.return_value = None
    return _OrchDouble(
        resultat,
        runner=MagicMock(),
        ticket_service=tickets,
        project_context="ctx",
        agent_configs=[],
        pipeline_log_path=tmp_path / "memory" / "log.md",
        livrer=livrer,
    )


async def test_livraison_started_emis_avant_livraison_done_sur_run_approuve(
    tmp_path: Path,
) -> None:
    resultat = PipelineResult(
        ticket_id="ticket-001",
        final_status=TicketStatus.done,
        rounds=1,
        approved=True,
        branch="ticket-001-slug",
        commit_sha="abc",
    )

    async def _livrer(_res: PipelineResult) -> Livraison:
        return Livraison(etapes=("pushed",))

    orc = _construire_double(tmp_path, resultat, _livrer)
    events: list[OrchestratorEvent] = []

    async def capture(ev: OrchestratorEvent) -> None:
        events.append(ev)

    await orc.run_pipeline("proj", "ticket-001", capture)

    types = [e.type for e in events]
    assert EventType.LIVRAISON_STARTED in types, "livraison_started absent"
    assert EventType.LIVRAISON_DONE in types, "livraison_done absent"
    assert types.index(EventType.LIVRAISON_STARTED) < types.index(
        EventType.LIVRAISON_DONE
    ), "livraison_started doit précéder livraison_done"


async def test_livraison_started_non_emis_sur_run_non_approuve(tmp_path: Path) -> None:
    # Un run refusé ne doit pas laisser croire qu'une livraison a commencé.
    resultat = PipelineResult(
        ticket_id="ticket-001",
        final_status=TicketStatus.blocked,
        rounds=1,
        approved=False,
    )

    async def _livrer(_res: PipelineResult) -> Livraison:
        return Livraison()

    orc = _construire_double(tmp_path, resultat, _livrer)
    events: list[OrchestratorEvent] = []

    async def capture(ev: OrchestratorEvent) -> None:
        events.append(ev)

    await orc.run_pipeline("proj", "ticket-001", capture)

    types = [e.type for e in events]
    assert EventType.LIVRAISON_STARTED not in types
    assert EventType.LIVRAISON_DONE not in types


# ------------------------------------------------------------------
# RunActif.etape mis à jour par _suivre
# ------------------------------------------------------------------


def test_run_actif_en_dict_contient_la_clef_etape() -> None:
    run = RunActif(run_id="r1", project_id="p")
    assert "etape" in run.en_dict()
    assert run.en_dict()["etape"] is None


def test_etape_vaut_validation_apres_validation_started() -> None:
    # L'observateur arrivé en cours de validation ne recevra plus qu'un
    # reviewer terminé : l'instantané lui dit que la validation est en cours.
    run = RunActif(run_id="r1", project_id="p")
    event = OrchestratorEvent(
        type=EventType.VALIDATION_STARTED,
        ticket_id="ticket-001",
        data={},
    )
    _suivre(run, event)
    assert run.etape == "validation"
    assert run.en_dict()["etape"] == "validation"


def test_etape_vaut_documentation_apres_documentation_started() -> None:
    run = RunActif(run_id="r1", project_id="p")
    _suivre(run, OrchestratorEvent(type=EventType.DOCUMENTATION_STARTED, ticket_id="t", data={}))
    assert run.etape == "documentation"


def test_etape_vaut_livraison_apres_livraison_started() -> None:
    run = RunActif(run_id="r1", project_id="p")
    _suivre(run, OrchestratorEvent(type=EventType.LIVRAISON_STARTED, ticket_id="t", data={}))
    assert run.etape == "livraison"


# ------------------------------------------------------------------
# validation_done.approved (ticket-279)
# ------------------------------------------------------------------


class _ValidateurKO:
    """Double du validateur qui retourne CHANGES_REQUESTED."""

    async def validate(self, **kwargs: object) -> ValidationResult:
        return ValidationResult(
            verdict="CHANGES_REQUESTED",
            all_passed=False,
            feedback="critère échoué",
            criteria=[CriterionResult(criterion="ça marche", passed=False, note="")],
        )


async def test_validation_done_porte_approved_true_pour_verdict_approved() -> None:
    # Le frontend lit ev.data["approved"] pour colorer le pipeline log.
    # Sans ce champ, il affichait toujours « refusée » (ticket-279).
    events: list[OrchestratorEvent] = []
    run = _run(events)
    orch = _Orch(_validator=_ValidateurOK())

    await stages.run_validation(orch, run, "")

    validation_done = next(e for e in events if e.type == EventType.VALIDATION_DONE)
    assert validation_done.data["approved"] is True


async def test_validation_done_porte_approved_false_pour_changes_requested() -> None:
    events: list[OrchestratorEvent] = []
    run = _run(events)
    orch = _Orch(_validator=_ValidateurKO())

    await stages.run_validation(orch, run, "")

    validation_done = next(e for e in events if e.type == EventType.VALIDATION_DONE)
    assert validation_done.data["approved"] is False
