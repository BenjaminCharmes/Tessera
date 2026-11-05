"""Stages read from persisted events — ticket-836 (ADR-078)."""
from datetime import datetime, timedelta, timezone

from tessera.services.anomalies.etapes import etapes_depuis
from tessera.services.anomalies.modeles import EvenementLu

T0 = datetime(2026, 11, 5, 10, 0, tzinfo=timezone.utc)


def _e(minute: int, type_: str, agent: str | None = None) -> EvenementLu:
    return EvenementLu(type=type_, agent=agent, ts=T0 + timedelta(minutes=minute))


def test_etapes_depuis_pairs_start_and_end_events_per_stage() -> None:
    evenements = [
        _e(0, "agent_started", "codeur"), _e(8, "agent_done", "codeur"),
        _e(9, "test_started"), _e(15, "test_result"),
        _e(16, "security_audit_started"), _e(17, "security_audit_done"),
        _e(18, "validation_started"), _e(19, "validation_done"),
        _e(20, "documentation_started"), _e(22, "doc_updated"),
        _e(23, "livraison_started"), _e(24, "livraison_done"),
    ]
    etapes = etapes_depuis(evenements)
    assert [(e.nom, e.fin is not None) for e in etapes] == [
        ("codeur", True), ("tests", True), ("securite", True),
        ("validation", True), ("documentation", True), ("livraison", True),
    ]
    assert etapes[0].debut == T0 and etapes[0].fin == T0 + timedelta(minutes=8)
    assert etapes[0].agent == "codeur" and etapes[1].agent is None


def test_etapes_depuis_closes_documentation_on_failure_too() -> None:
    etapes = etapes_depuis([_e(0, "documentation_started"), _e(1, "documentation_failed")])
    assert etapes[0].fin is not None


def test_etapes_depuis_leaves_an_unclosed_stage_open() -> None:
    etapes = etapes_depuis([_e(0, "test_started")])
    assert len(etapes) == 1
    assert etapes[0].fin is None and not etapes[0].abandonnee


def test_etapes_depuis_marks_a_restarted_stage_as_abandoned() -> None:
    etapes = etapes_depuis(
        [_e(0, "test_started"), _e(5, "test_started"), _e(9, "test_result")]
    )
    assert [(e.debut, e.abandonnee, e.fin is None) for e in etapes] == [
        (T0, True, True),
        (T0 + timedelta(minutes=5), False, False),
    ]


def test_etapes_depuis_keeps_review_and_validation_apart_when_they_overlap() -> None:
    etapes = etapes_depuis(
        [
            _e(0, "agent_started", "reviewer"), _e(1, "validation_started"),
            _e(4, "agent_done", "reviewer"), _e(6, "validation_done"),
        ]
    )
    durees = {e.nom: (e.fin - e.debut).total_seconds() for e in etapes if e.fin}
    assert durees == {"reviewer": 240.0, "validation": 300.0}


def test_etapes_depuis_ignores_an_end_without_start_and_unrelated_events() -> None:
    assert etapes_depuis([_e(0, "test_result"), _e(1, "ticket_status_changed")]) == []
