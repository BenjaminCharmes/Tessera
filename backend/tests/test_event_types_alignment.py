"""Alignement des types d'événements backend ↔ frontend — ticket-054.

L'union TypeScript était restée à six valeurs alors que le pipeline en émettait
quatorze : les événements manquants traversaient l'UI sans type, donc sans
traitement possible, et rien ne le signalait. Ce test est le garde-fou.
"""
import re
from pathlib import Path

from tessera.services.pipeline_events import EventType

_TS_TYPES = Path(__file__).resolve().parents[2] / "frontend" / "src" / "types" / "api.ts"

# Émis par le backend avant que l'UI ne les lise : le ticket-559 ne touche pas
# à `frontend/`, le ticket-564 ajoute ces deux types à l'union. Dès qu'il le
# fait, le second test ci-dessous échoue tant que cette liste n'est pas vidée.
_EN_ATTENTE_DU_FRONTEND = frozenset({"external_wait", "conflict_resolution"})


def test_chaque_evenement_backend_existe_cote_frontend() -> None:
    source = _TS_TYPES.read_text(encoding="utf-8")
    union = re.search(r"export type EventType =(.*?);", source, re.S)
    assert union is not None, "union EventType introuvable dans api.ts"

    declared = set(re.findall(r'"([a-z_]+)"', union.group(1)))
    emitted = {e.value for e in EventType} - _EN_ATTENTE_DU_FRONTEND

    assert emitted <= declared, (
        "Événements émis par le backend et absents du frontend : "
        f"{sorted(emitted - declared)}"
    )


def test_la_liste_d_attente_du_frontend_ne_garde_que_l_absent() -> None:
    # Une entrée déjà déclarée côté UI n'attend plus rien : on la retire.
    source = _TS_TYPES.read_text(encoding="utf-8")
    union = re.search(r"export type EventType =(.*?);", source, re.S)
    assert union is not None

    declared = set(re.findall(r'"([a-z_]+)"', union.group(1)))

    assert _EN_ATTENTE_DU_FRONTEND.isdisjoint(declared), (
        "Déclarés côté frontend : retirer de _EN_ATTENTE_DU_FRONTEND "
        f"{sorted(_EN_ATTENTE_DU_FRONTEND & declared)}"
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
