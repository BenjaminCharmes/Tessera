"""La question en attente voyage dans l'instantane — ticket-163.

Un agent a pose une question et attendu 5 min 39 sans que rien ne s'affiche :
l'etat du run ne se reconstruisait que depuis les evenements recus en direct,
et `agent_question` etait passe avant que l'onglet ne regarde.
"""

from tessera.models.agent import AgentRole
from tessera.services.pipeline_events import EventType, OrchestratorEvent
from tessera.services.run_executor import _suivre
from tessera.services.run_registry import RunActif


def _run() -> RunActif:
    return RunActif(run_id="r1", project_id="demineur", ticket_id="ticket-001")


def _evenement(type_: EventType, **data: object) -> OrchestratorEvent:
    return OrchestratorEvent(
        type=type_, ticket_id="ticket-001", agent=AgentRole.codeur, data=dict(data)
    )


def test_une_question_posee_est_retenue() -> None:
    run = _run()

    _suivre(run, _evenement(EventType.AGENT_QUESTION, question="On casse l'API ?"))

    assert run.question == "On casse l'API ?"


def test_la_question_part_dans_l_instantane() -> None:
    """Sans ca, un observateur qui arrive apres ne la verra jamais."""
    run = _run()
    _suivre(run, _evenement(EventType.AGENT_QUESTION, question="On casse l'API ?"))

    assert run.en_dict()["question"] == "On casse l'API ?"


def test_l_activite_qui_suit_efface_la_question() -> None:
    """L'agent a repris — de lui-meme ou sur reponse : la question n'attend plus.

    La laisser afficherait une question morte, ce qui est pire que rien : on
    repondrait a un agent qui n'ecoute plus.
    """
    run = _run()
    _suivre(run, _evenement(EventType.AGENT_QUESTION, question="On casse l'API ?"))

    _suivre(run, _evenement(EventType.AGENT_TOKEN, token="Je reprends"))

    assert run.question is None


def test_un_usage_d_outil_efface_aussi_la_question() -> None:
    run = _run()
    _suivre(run, _evenement(EventType.AGENT_QUESTION, question="?"))

    _suivre(run, _evenement(EventType.AGENT_TOOL_USE, tool="Read"))

    assert run.question is None


def test_sans_question_le_champ_reste_vide() -> None:
    run = _run()

    _suivre(run, _evenement(EventType.AGENT_STARTED, round=1))

    assert run.en_dict()["question"] is None
