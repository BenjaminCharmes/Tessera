from __future__ import annotations

from pathlib import Path
from typing import Any

import aiosqlite
from pydantic import BaseModel

from tessera.services.cost_aggregate import CostColumn, aggregate_cost


class TicketUsage(BaseModel):
    ticket_id: str
    total_cost_usd: float
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    call_count: int


class ProjectUsage(BaseModel):
    total_cost_usd: float
    total_tokens: int
    total_runs: int
    per_ticket: list[TicketUsage]


async def get_project_usage(
    db_path: Path | str,
    project_id: str,
) -> dict[str, Any]:
    async with aiosqlite.connect(str(db_path)) as db:
        db.row_factory = aiosqlite.Row

        async with db.execute(
            """SELECT COUNT(DISTINCT pr.id) as total_runs,
                      COALESCE(SUM(ac.cost_usd), 0.0) as total_cost_usd,
                      COALESCE(SUM(ac.input_tokens + ac.output_tokens + ac.cache_read_tokens), 0) as total_tokens
               FROM pipeline_runs pr
               LEFT JOIN agent_calls ac ON ac.run_id = pr.id
               WHERE pr.project_id=?""",
            (project_id,),
        ) as cursor:
            summary = await cursor.fetchone()

        async with db.execute(
            """SELECT ac.ticket_id,
                      COALESCE(SUM(ac.cost_usd), 0.0) as total_cost_usd,
                      COALESCE(SUM(ac.input_tokens), 0) as input_tokens,
                      COALESCE(SUM(ac.output_tokens), 0) as output_tokens,
                      COALESCE(SUM(ac.cache_read_tokens), 0) as cache_read_tokens,
                      COUNT(*) as call_count
               FROM agent_calls ac
               JOIN pipeline_runs pr ON ac.run_id = pr.id
               WHERE pr.project_id=?
               GROUP BY ac.ticket_id
               ORDER BY total_cost_usd DESC""",
            (project_id,),
        ) as cursor:
            ticket_rows = await cursor.fetchall()

    total_cost_usd = float(summary["total_cost_usd"]) if summary else 0.0
    total_tokens = int(summary["total_tokens"]) if summary else 0
    total_runs = int(summary["total_runs"]) if summary else 0
    return {
        "total_cost_usd": total_cost_usd,
        "total_tokens": total_tokens,
        "total_runs": total_runs,
        "per_ticket": [
            {
                "ticket_id": row["ticket_id"],
                "total_cost_usd": float(row["total_cost_usd"]),
                "input_tokens": int(row["input_tokens"]),
                "output_tokens": int(row["output_tokens"]),
                "cache_read_tokens": int(row["cache_read_tokens"]),
                "call_count": int(row["call_count"]),
            }
            for row in ticket_rows
        ],
    }


async def get_usage_breakdown(
    db_path: Path | str,
    project_id: str | None = None,
) -> dict[str, Any]:
    """La dépense ventilée par agent et par modèle — ticket-077.

    `get_project_usage` donne le total et le détail par ticket. Il manquait la
    ventilation qui permet d'agir : **par agent**, parce qu'elle dit qui
    consomme — un codeur qui mange 70 % du budget, ou un reviewer plus cher que
    prévu parce qu'il relit tout le diff à chaque tour — et **par modèle**, pour
    préparer l'arbitrage du jour où l'on descend un agent en Haiku.

    `project_id` à `None` couvre **tous** les projets : la question « combien me
    coûte Tessera ce mois-ci » n'avait aucune réponse, chaque endpoint étant
    borné à un projet.
    """
    where = "pr.project_id = ?" if project_id is not None else "1 = 1"
    params: tuple[Any, ...] = (project_id,) if project_id is not None else ()

    async def _lignes(
        db: aiosqlite.Connection, colonne: CostColumn, nom: str
    ) -> list[dict[str, Any]]:
        return [
            {
                nom: ligne.key,
                "total_cost_usd": ligne.cost_usd,
                "total_tokens": ligne.tokens,
                "call_count": ligne.calls,
            }
            for ligne in await aggregate_cost(db, colonne, where, params)
        ]

    async with aiosqlite.connect(str(db_path)) as db:
        db.row_factory = aiosqlite.Row
        per_agent = await _lignes(db, "ac.role", "role")
        per_model = await _lignes(db, "ac.model", "model")
        # Ventiler par projet quand on en regarde un seul n'apprendrait rien :
        # cette clé ne se remplit que sur la vue d'ensemble (ticket-082).
        per_project = (
            await _lignes(db, "pr.project_id", "project_id") if project_id is None else []
        )

    return {
        "project_id": project_id,
        "total_cost_usd": round(sum(a["total_cost_usd"] for a in per_agent), 10),
        "per_agent": per_agent,
        "per_model": per_model,
        "per_project": per_project,
    }
