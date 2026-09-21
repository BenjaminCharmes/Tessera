"""Alignement des types d'événements backend ↔ frontend — ticket-054.

L'union TypeScript était restée à six valeurs alors que le pipeline en émettait
quatorze : les événements manquants traversaient l'UI sans type, donc sans
traitement possible, et rien ne le signalait. Ce test est le garde-fou.
"""
import re
from pathlib import Path

from tessera.services.pipeline_events import EventType

_TS_TYPES = Path(__file__).resolve().parents[2] / "frontend" / "src" / "types" / "api.ts"


def test_chaque_evenement_backend_existe_cote_frontend() -> None:
    source = _TS_TYPES.read_text(encoding="utf-8")
    union = re.search(r"export type EventType =(.*?);", source, re.S)
    assert union is not None, "union EventType introuvable dans api.ts"

    declared = set(re.findall(r'"([a-z_]+)"', union.group(1)))
    emitted = {e.value for e in EventType}

    assert emitted <= declared, (
        "Événements émis par le backend et absents du frontend : "
        f"{sorted(emitted - declared)}"
    )


def test_le_frontend_ne_declare_pas_d_evenement_fantome() -> None:
    # L'inverse compte aussi : un type déclaré côté UI et jamais émis fait
    # écrire du code mort qu'aucun test ne peut atteindre.
    source = _TS_TYPES.read_text(encoding="utf-8")
    union = re.search(r"export type EventType =(.*?);", source, re.S)
    assert union is not None

    declared = set(re.findall(r'"([a-z_]+)"', union.group(1)))
    emitted = {e.value for e in EventType}

    assert declared <= emitted, (
        f"Événements déclarés côté frontend et jamais émis : {sorted(declared - emitted)}"
    )
