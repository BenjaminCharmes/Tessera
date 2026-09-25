"""La question en attente voyage dans l'instantane — ticket-163.

Un agent a pose une question et attendu 5 min 39 sans que rien ne s'affiche :
l'etat du run ne se reconstruisait que depuis les evenements recus en direct,
et `agent_question` etait passe avant que l'onglet ne regarde.
"""

import pytest

from datetime import datetime, timedelta, timezone

from tessera.config import settings
from tessera.models.agent import AgentRole
from tessera.services.pipeline_events import EventType, OrchestratorEvent
from tessera.services.run_executor import _suivre, dialogue_du_run
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


def test_the_deadline_travels_with_the_question() -> None:
    """Sans elle, cinq minutes de silence se lisent comme une panne."""
    run = _run()

    _suivre(
        run,
        _evenement(
            EventType.AGENT_QUESTION,
            question="On casse l'API ?",
            expire_a="2026-09-25T09:00:00+00:00",
        ),
    )

    assert run.en_dict()["question_expire_a"] == "2026-09-25T09:00:00+00:00"


def test_activity_clears_the_deadline_with_the_question() -> None:
    run = _run()
    _suivre(
        run,
        _evenement(
            EventType.AGENT_QUESTION, question="?", expire_a="2026-09-25T09:00:00+00:00"
        ),
    )

    _suivre(run, _evenement(EventType.AGENT_TOKEN, token="Je reprends"))

    assert run.question_expire_a is None


@pytest.mark.asyncio
async def test_the_channel_announces_when_the_agent_will_move_on(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """L'échéance est absolue : un client tardif doit savoir ce qui reste."""
    monkeypatch.setattr(settings, "dialogue_timeout_s", 0.01)
    recus: list[OrchestratorEvent] = []

    async def envoyer(event: OrchestratorEvent) -> None:
        recus.append(event)

    canal = dialogue_du_run(envoyer, _run())
    await canal.ask("On casse l'API ?")

    question = next(e for e in recus if e.type is EventType.AGENT_QUESTION)
    expire = datetime.fromisoformat(str(question.data["expire_a"]))
    assert expire > datetime.now(timezone.utc) - timedelta(seconds=5)
