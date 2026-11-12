"""Documentation refused several batches in a row — ticket-950 (ADR-078)."""
from pathlib import Path

from tessera.services.supervision.anomalies.lecture_historique import derniers_lots_de_documentation
from tessera.services.supervision.anomalies.modeles import LotDoc
from tessera.services.supervision.anomalies.regles_historiques import documentation_refusee_en_serie
from tests.anomalies_base import base_neuve, evenement, ligne_de_run

MOTIF = "motif secret de refus sur le fichier docs/guide.md"


def _refuse(id_: int) -> LotDoc:
    return LotDoc(id=id_, fichiers=0, refus=1)


def test_three_refused_batches_without_file_report() -> None:
    a = documentation_refusee_en_serie([_refuse(9), _refuse(8), _refuse(7)], ticket_id="t-1")
    assert a is not None
    assert (a.regle, a.cle, a.mesure, a.seuil, a.unite) == (
        "documentation_refusee_en_serie", "documentation_refusee:9", 3.0, 3.0, "runs",
    )


def test_two_refused_batches_then_a_changed_file_is_none() -> None:
    lots = [_refuse(9), _refuse(8), LotDoc(id=7, fichiers=1, refus=1)]
    assert documentation_refusee_en_serie(lots, ticket_id="t-1") is None
    lots = [_refuse(9), LotDoc(id=8, fichiers=0, refus=0), _refuse(7)]
    assert documentation_refusee_en_serie(lots, ticket_id="t-1") is None


def test_fewer_than_three_batches_is_none() -> None:
    assert documentation_refusee_en_serie([_refuse(2), _refuse(1)], ticket_id="t-1") is None
    assert documentation_refusee_en_serie([], ticket_id="t-1") is None


def test_message_never_carries_a_refusal_text() -> None:
    a = documentation_refusee_en_serie([_refuse(3), _refuse(2), _refuse(1)], ticket_id="t-1")
    assert a is not None and MOTIF not in a.message


async def test_derniers_lots_reads_only_the_project_newest_first(tmp_path: Path) -> None:
    db = await base_neuve(tmp_path / "t.db")
    await ligne_de_run(db, "r1")
    await ligne_de_run(db, "r2")
    await ligne_de_run(db, "autre", project_id="q")
    ts = "2026-11-05T10:00:00+00:00"
    await evenement(db, "r1", "doc_updated", ts=ts, data={"fichiers": ["a.md"], "refus": []})
    await evenement(db, "autre", "doc_updated", ts=ts, data={"fichiers": [], "refus": [MOTIF]})
    await evenement(db, "r1", "run_anomaly", ts=ts, data={"refus": [MOTIF]})
    dernier = await evenement(db, "r2", "doc_updated", ts=ts, data={"fichiers": [], "refus": [MOTIF]})
    lots = await derniers_lots_de_documentation(db, "p")
    assert [(lot.fichiers, lot.refus) for lot in lots] == [(0, 1), (1, 0)]
    assert lots[0].id == dernier
