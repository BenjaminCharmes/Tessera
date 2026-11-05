"""Reading the history of a project — tickets 836 to 838 (ADR-078).

Le second des deux fichiers du détecteur à toucher SQLite, en lecture seule.
Chaque lecture est bornée : jamais toute la table `agent_events`.
"""
from datetime import datetime
from pathlib import Path
from typing import Any

from tessera.services.supervision.anomalies.etapes import etapes_depuis, types_de_l_etape
from tessera.services.supervision.anomalies.lecture_base import ouvrir_en_lecture
from tessera.services.supervision.anomalies.modeles import EvenementLu, LigneOuverte, RunFini

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


#: Un run `single` : une ligne sans mode date d'avant le ticket-263 et se lit `single`.
_SINGLE = "(r.mode IS NULL OR r.mode = 'single')"


async def couts_passes(db_path: Path | str, project_id: str, n: int = 20) -> list[float]:
    """Cost (USD) of the `n` latest finished `single` runs of the project, newest first.

    Les enveloppes de file ne portent aucun appel d'agent ; un run à coût nul
    n'est pas un échantillon.
    """
    requete = f"""
        SELECT SUM(c.cost_usd) AS cout
        FROM pipeline_runs r JOIN agent_calls c ON c.run_id = r.id
        WHERE r.project_id = ? AND {_SINGLE} AND r.finished_at IS NOT NULL
        GROUP BY r.id HAVING cout > 0
        ORDER BY r.started_at DESC, r.rowid DESC LIMIT ?
    """  # noqa: S608 — `_SINGLE` est une constante du module
    async with ouvrir_en_lecture(db_path) as db:
        async with db.execute(requete, (project_id, n)) as curseur:
            return [float(ligne[0]) for ligne in await curseur.fetchall()]


async def ligne_ouverte_du_ticket(
    db_path: Path | str, project_id: str, ticket_id: str
) -> LigneOuverte | None:
    """The unfinished `single` row of the ticket, if any."""
    requete = f"""
        SELECT r.id, r.ticket_id, r.started_at FROM pipeline_runs r
        WHERE r.project_id = ? AND r.ticket_id = ? AND {_SINGLE} AND r.finished_at IS NULL
        ORDER BY r.started_at DESC, r.rowid DESC LIMIT 1
    """  # noqa: S608
    async with ouvrir_en_lecture(db_path) as db:
        async with db.execute(requete, (project_id, ticket_id)) as curseur:
            ligne = await curseur.fetchone()
    return None if ligne is None else LigneOuverte(ligne[0], ligne[1], ligne[2])


async def cout_du_ticket(db_path: Path | str, run_row_id: str) -> float:
    """What the agent calls of one `pipeline_runs` row cost so far."""
    async with ouvrir_en_lecture(db_path) as db:
        async with db.execute(
            "SELECT COALESCE(SUM(cost_usd), 0.0) FROM agent_calls WHERE run_id = ?",
            (run_row_id,),
        ) as curseur:
            ligne = await curseur.fetchone()
    return float(ligne[0]) if ligne else 0.0


async def derniers_runs_finis(
    db_path: Path | str, project_id: str, ticket_id: str, n: int = 2
) -> list[RunFini]:
    """The `n` latest finished `single` runs of the ticket, newest first.

    Les enveloppes de file et la ligne encore ouverte n'en font pas partie.
    """
    requete = f"""
        SELECT r.id, r.ticket_id, r.final_status, r.arret FROM pipeline_runs r
        WHERE r.project_id = ? AND r.ticket_id = ? AND {_SINGLE} AND r.finished_at IS NOT NULL
        ORDER BY r.started_at DESC, r.rowid DESC LIMIT ?
    """  # noqa: S608
    async with ouvrir_en_lecture(db_path) as db:
        async with db.execute(requete, (project_id, ticket_id, n)) as curseur:
            return [RunFini(*ligne) for ligne in await curseur.fetchall()]
