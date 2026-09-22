"""Tests unitaires des étapes du pipeline — ticket-046.

Les tests de `test_orchestrator.py` exercent l'enchaînement complet. Ceux-ci
exercent chaque étape isolément : c'est ce que la décomposition rend possible,
et ce qui permet de couvrir un cas limite sans monter tout un pipeline.
"""
from pathlib import Path

import pytest

from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services import pipeline_stages as stages
from tessera.services.git_workspace import GitCommandError
from tessera.services.pipeline_events import EventType, OrchestratorEvent
from tessera.services.pipeline_run import PipelineRun


def _ticket(**kwargs: object) -> Ticket:
    base = dict(
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
    """Orchestrateur minimal : seuls les attributs que l'étape testée lit."""

    def __init__(self, **attrs: object) -> None:
        self._git_workspace = None
        self._project_context = "contexte projet"
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

    return PipelineRun(project_id="projet", ticket=_ticket(), on_event=_on_event)


# ------------------------------------------------------------------
# build_context
# ------------------------------------------------------------------


def test_build_context_sans_retour_rend_le_contexte_projet_tel_quel() -> None:
    assert stages.build_context(_Orch(), _run()) == "contexte projet"


def test_build_context_accumule_les_retours_du_reviewer() -> None:
    run = _run()
    run.review_feedback = ["manque des tests", "nommage à revoir"]

    context = stages.build_context(_Orch(), run)

    assert context.startswith("contexte projet")
    assert "Tour 1: manque des tests" in context
    assert "Tour 2: nommage à revoir" in context


# ------------------------------------------------------------------
# ensure_clean_tree
# ------------------------------------------------------------------


async def test_ensure_clean_tree_laisse_passer_sans_git() -> None:
    assert await stages.ensure_clean_tree(_Orch(), _run()) is None


async def test_ensure_clean_tree_bloque_le_ticket_sur_un_arbre_sale() -> None:
    # Le ticket ne doit surtout pas rester en `todo` : `pick_next_ticket` le
    # resservirait à chaque slot restant d'un run autonome.
    class _DirtyGit:
        async def is_clean(self) -> bool:
            return False

    class _TicketSvc:
        def __init__(self) -> None:
            self.statuses: list[TicketStatus] = []

        async def update_status(self, ticket_id: str, status: TicketStatus) -> None:
            self.statuses.append(status)

    svc = _TicketSvc()
    events: list[OrchestratorEvent] = []
    orch = _Orch(_git_workspace=_DirtyGit(), _ticket_svc=svc)

    result = await stages.ensure_clean_tree(orch, _run(events))

    assert result is not None
    assert result.final_status == TicketStatus.blocked
    assert result.rounds == 0
    assert svc.statuses == [TicketStatus.blocked]
    assert any(e.type == EventType.ERROR for e in events)


async def test_ensure_clean_tree_laisse_passer_si_le_controle_git_echoue() -> None:
    # Un dépôt cassé ne doit pas empêcher de travailler : le garde-fou est un
    # filet de sécurité, pas une condition de démarrage.
    class _BrokenGit:
        async def is_clean(self) -> bool:
            raise GitCommandError(command=["git", "status"], returncode=128, stderr="boom")

    assert await stages.ensure_clean_tree(_Orch(_git_workspace=_BrokenGit()), _run()) is None


# ------------------------------------------------------------------
# create_branch
# ------------------------------------------------------------------


async def test_create_branch_degrade_sans_depot_git() -> None:
    # Un projet sans dépôt git reste utilisable : on continue sans branche.
    class _NoRepoGit:
        async def create_branch(self, ticket_id: str, slug: str) -> str:
            raise GitCommandError(command=["git", "checkout"], returncode=128, stderr="not a repo")

    run = _run()
    await stages.create_branch(_Orch(_git_workspace=_NoRepoGit()), run)

    assert run.branch is None


async def test_create_branch_renseigne_la_branche_et_emet_l_evenement() -> None:
    class _Git:
        async def create_branch(self, ticket_id: str, slug: str) -> str:
            return f"{ticket_id}-slug"

    events: list[OrchestratorEvent] = []
    run = _run(events)
    await stages.create_branch(_Orch(_git_workspace=_Git()), run)

    assert run.branch == "ticket-001-slug"
    assert [e.type for e in events] == [EventType.BRANCH_CREATED]


# ------------------------------------------------------------------
# PipelineRun.start_round
# ------------------------------------------------------------------


def test_start_round_remet_a_zero_l_etat_du_tour() -> None:
    # Sans ce reset, un second tour relirait le diff du premier.
    run = _run()
    run.reviewed_code = "diff du tour 1"
    run.test_context = "tests du tour 1"
    run.security_context = "audit du tour 1"
    run.review_feedback = ["à garder entre les tours"]

    run.start_round(2)

    assert run.round_num == 2
    assert run.reviewed_code == ""
    assert run.test_context == ""
    assert run.security_context == ""
    assert run.review_feedback == ["à garder entre les tours"]


# ------------------------------------------------------------------
# Messages spontanes de l'utilisateur — ticket-066
# ------------------------------------------------------------------


def test_build_context_injecte_les_messages_spontanes() -> None:
    # Le pipeline etait un tuyau ferme : une consigne donnee pendant un run
    # n'arrivait jamais a l'agent. Elle est desormais lue au tour suivant.
    run = _run()
    run.dialogue.interject("utilise pathlib, pas os.path")

    contexte = stages.build_context(_Orch(), run)

    assert "utilise pathlib, pas os.path" in contexte
    assert "contexte projet" in contexte


def test_un_message_spontane_n_est_injecte_qu_une_fois() -> None:
    # Sinon la consigne se repeterait a chaque tour, en gonflant le contexte
    # a chaque fois un peu plus.
    run = _run()
    run.dialogue.interject("pense aux tests")

    premier = stages.build_context(_Orch(), run)
    second = stages.build_context(_Orch(), run)

    assert "pense aux tests" in premier
    assert "pense aux tests" not in second


def test_build_context_sans_message_spontane_est_inchange() -> None:
    assert stages.build_context(_Orch(), _run()) == "contexte projet"


def test_l_outil_ask_user_n_est_offert_qu_en_mode_interactif() -> None:
    # Offrir `ask_user` a un run non interactif promettrait a l'agent une
    # réponse que personne ne peut donner : il attendrait le delai complet a
    # chaque question, pour rien (ADR-025).
    from tessera.services.dialogue import DialogueChannel

    run = _run()
    assert stages.asker_for(run) is None

    run.dialogue = DialogueChannel(interactive=True)
    assert stages.asker_for(run) == run.dialogue.ask


# ------------------------------------------------------------------
# Sécurité et validation échouent fermé — ticket-122
# ------------------------------------------------------------------


class _Tickets:
    def __init__(self) -> None:
        self.statuts: list[TicketStatus] = []

    async def update_status(self, ticket_id: str, status: TicketStatus) -> None:
        self.statuts.append(status)


class _AuditeurEnPanne:
    async def audit(self, code_diff: str, project_path: Path) -> object:
        raise RuntimeError("provider down")


class _ValidateurEnPanne:
    async def validate(self, **kwargs: object) -> object:
        raise RuntimeError("provider down")


async def test_une_panne_de_l_auditeur_bloque_le_run() -> None:
    # L'exception était avalée et l'audit sauté : un diff non audité arrivait
    # au reviewer comme s'il était propre. Une panne n'est pas un PASS.
    events: list[OrchestratorEvent] = []
    run = _run(events)
    run.reviewed_code = "diff"
    orch = _Orch(
        _security_auditor=_AuditeurEnPanne(),
        _project_path=Path("."),
        _ticket_svc=_Tickets(),
    )

    result = await stages.run_security_audit(orch, run)

    assert result is not None
    assert result.final_status is TicketStatus.blocked
    done = [e for e in events if e.type == EventType.SECURITY_AUDIT_DONE]
    assert done and done[0].data["verdict"] == "BLOCK"
    assert "provider down" in done[0].data["reason"]
    assert [e.type for e in events][-1] is EventType.PIPELINE_DONE


async def test_une_panne_du_validateur_demande_des_changements() -> None:
    # Même raisonnement : l'exception valait approbation.
    events: list[OrchestratorEvent] = []
    run = _run(events)
    orch = _Orch(_validator=_ValidateurEnPanne())

    approved, reason = await stages.run_validation(orch, run, "")

    assert approved is False
    assert "provider down" in reason
