"""Reading the events of one ticket — tickets 835 and 836 (ADR-078).

Un des deux seuls fichiers du détecteur à toucher SQLite, en lecture seule.
"""
import hashlib
import json
from pathlib import Path
from typing import Any

from tessera.services.anomalies.lecture_base import ouvrir_en_lecture
from tessera.services.anomalies.modeles import AppelOutil

__all__ = ["AppelOutil", "derniers_appels_d_outils", "hacher_input"]


def hacher_input(entree: Any) -> str:
    """Hash the canonical JSON of a tool input (keys sorted, so order never matters)."""
    canonique = json.dumps(entree, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonique.encode("utf-8")).hexdigest()[:16]


async def derniers_appels_d_outils(
    db_path: Path | str, run_id: str, ticket_id: str, n: int = 8
) -> list[AppelOutil]:
    """The `n` latest tool calls of the ticket since its last `agent_started`, oldest first."""
    requete = """
        SELECT id, agent, data_json FROM agent_events
        WHERE run_id = ? AND ticket_id = ? AND type = 'agent_tool_use'
          AND id > COALESCE((SELECT MAX(id) FROM agent_events
                             WHERE run_id = ? AND ticket_id = ? AND type = 'agent_started'), 0)
        ORDER BY id DESC LIMIT ?
    """
    async with ouvrir_en_lecture(db_path) as db:
        async with db.execute(requete, (run_id, ticket_id, run_id, ticket_id, n)) as curseur:
            lignes = await curseur.fetchall()
    appels = []
    for id_, agent, data_json in reversed(list(lignes)):
        data = json.loads(data_json or "{}")
        appels.append(
            AppelOutil(
                id=int(id_), agent=agent, tool=str(data.get("tool", "")),
                input_hash=hacher_input(data.get("input")), ticket_id=ticket_id,
            )
        )
    return appels
