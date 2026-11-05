"""Reading the history of a project — tickets 836 to 838 (ADR-078).

Le second des deux fichiers du détecteur à toucher SQLite, en lecture seule.
Chaque lecture est bornée : jamais toute la table `agent_events`.
"""
from datetime import datetime
from pathlib import Path
from typing import Any

from tessera.services.anomalies.etapes import etapes_depuis, types_de_l_etape
from tessera.services.anomalies.lecture_base import ouvrir_en_lecture
from tessera.services.anomalies.modeles import EvenementLu

#: Lignes lues par type d'événement : de quoi couvrir 20 étapes, sans la table entière.
BORNE_PAR_TYPE = 200

_EVENEMENTS_DU_PROJET = """
    SELECT e.id, e.run_id, e.ticket_id, e.type, e.agent, e.ts
    FROM agent_events e JOIN pipeline_runs r ON r.id = e.run_id
    WHERE r.project_id = ? AND e.type = ? AND (? IS NULL OR e.agent = ?)
    ORDER BY e.id DESC LIMIT ?
"""


async def durees_passees(
    db_path: Path | str, project_id: str, etape: str, n: int = 20
) -> list[float]:
    """Durations (s) of the `n` latest closed stages `etape` of the project, newest first."""
    debut, fins, agent = types_de_l_etape(etape)
    lignes: list[Any] = []
    async with ouvrir_en_lecture(db_path) as db:
        for type_ in (debut, *fins):
            async with db.execute(
                _EVENEMENTS_DU_PROJET, (project_id, type_, agent, agent, BORNE_PAR_TYPE)
            ) as curseur:
                lignes.extend(await curseur.fetchall())
    # L'ordre d'écriture fait foi : `id` croît avec les événements, `ts` peut égaler.
    lignes.sort(key=lambda ligne: int(ligne[0]))
    par_flux: dict[tuple[str, str | None], list[EvenementLu]] = {}
    for _id, run_id, ticket_id, type_, agent_ligne, ts in lignes:
        par_flux.setdefault((run_id, ticket_id), []).append(
            EvenementLu(type=type_, agent=agent_ligne, ts=datetime.fromisoformat(ts))
        )
    closes = [
        e
        for flux in par_flux.values()
        for e in etapes_depuis(flux)
        if e.fin is not None and not e.abandonnee
    ]
    closes.sort(key=lambda e: e.debut, reverse=True)
    return [(e.fin - e.debut).total_seconds() for e in closes[:n] if e.fin is not None]
