"""The base of the anomaly detector — ticket-834 (ADR-078)."""
import asyncio
from typing import Any

import pytest
from pydantic import ValidationError

from tessera.config import Settings
from tessera.models.agent import AgentRole
from tessera.services.anomalies.modeles import Anomalie
from tessera.services.event_hub import JETABLES, Abonnement, EventHub
from tessera.services.pipeline_events import EventType, OrchestratorEvent
from tessera.services.run_registry import RunActif, RunRegistry
from tessera.services.run_suivi import suivre


def _ev(type_: EventType, agent: AgentRole | None = None, **data: Any) -> OrchestratorEvent:
    return OrchestratorEvent(type=type_, agent=agent, ticket_id="ticket-001", data=data)


def _anomalie(cle: str = "k", message: str = "m") -> Anomalie:
    return Anomalie(
        regle="silence", cle=cle, ticket_id="ticket-001", message=message,
        mesure=900.0, seuil=900.0, unite="s",
    )


def test_en_dict_exposes_anomalies_and_hides_the_seen_keys() -> None:
    run = RunActif(run_id="r", project_id="p")
    run.ajouter_anomalie(_anomalie().model_dump())
    run.anomalies_vues.add("k")
    d = run.en_dict()
    assert d["anomalies"][0]["cle"] == "k"
    assert "anomalies_vues" not in d


def test_suivre_sets_last_event_time_on_every_event_type() -> None:
    for type_ in (EventType.AGENT_TOKEN, EventType.AGENT_TOOL_USE, EventType.TICKET_STATUS_CHANGED):
        run = RunActif(run_id="r", project_id="p")
        assert run.dernier_evenement_a is None
        event = _ev(type_, AgentRole.codeur)
        suivre(run, event)
        assert run.dernier_evenement_a == event.timestamp


def test_suivre_tracks_external_wait() -> None:
    run = RunActif(run_id="r", project_id="p")
    suivre(run, _ev(EventType.EXTERNAL_WAIT, waiting=True))
    assert run.attente_exterieure is True
    suivre(run, _ev(EventType.EXTERNAL_WAIT, waiting=False))
    assert run.attente_exterieure is False


def test_registry_vivants_lists_open_runs_only() -> None:
    registre = RunRegistry()
    a = registre.ouvrir("p1")
    registre.ouvrir("p2")
    registre.fermer(a.run_id)
    assert [r.project_id for r in registre.vivants()] == ["p2"]


def test_run_anomaly_is_not_droppable() -> None:
    assert EventType.RUN_ANOMALY not in JETABLES

    async def saturer() -> list[OrchestratorEvent]:
        abonnement = Abonnement(2, EventHub())
        for _ in range(5):
            abonnement.deposer(_ev(EventType.AGENT_TOKEN, AgentRole.codeur))
        abonnement.deposer(_ev(EventType.RUN_ANOMALY))
        return abonnement.vider()

    recus = asyncio.run(saturer())
    assert EventType.RUN_ANOMALY in [e.type for e in recus]


def test_anomalie_message_at_200_chars_is_kept() -> None:
    assert len(_anomalie(message="x" * 200).message) == 200


def test_anomalie_message_at_201_chars_is_refused() -> None:
    with pytest.raises(ValidationError):
        _anomalie(message="x" * 201)


def test_anomalies_list_keeps_the_20_most_recent() -> None:
    run = RunActif(run_id="r", project_id="p")
    for i in range(21):
        run.ajouter_anomalie(_anomalie(cle=f"k{i}").model_dump())
    cles = [a["cle"] for a in run.anomalies]
    assert len(cles) == 20
    assert cles[0] == "k1" and cles[-1] == "k20"


def test_anomaly_settings_defaults() -> None:
    s = Settings()
    assert s.anomalies_actives is True
    assert s.anomalie_intervalle_s == 300.0
    assert s.anomalie_outil_repete == 4
    assert s.anomalie_silence_s == 900.0
    assert s.anomalie_tours == 3
    assert s.anomalie_facteur_median == 3.0
    assert s.anomalie_echantillon_min == 10
    assert s.anomalie_fenetre == 20
    assert s.anomalie_plancher_etape_s == 300.0
    assert s.anomalie_plancher_cout_usd == 0.5
    assert s.anomalie_part_budget == 0.8


def test_suivre_ignores_the_detector_own_event_for_the_silence_clock() -> None:
    run = RunActif(run_id="r", project_id="p")
    suivre(run, _ev(EventType.RUN_ANOMALY))
    assert run.dernier_evenement_a is None
