"""The one query that sums agent-call cost by role, model or project — ticket-678.

`get_usage_breakdown` (sans fenêtre de temps) et `usage_stats` (sur une
période) agrégeaient chacun le coût par rôle avec leur propre requête. Les deux
passent désormais ici : seul le filtre `WHERE` change.
"""
from dataclasses import dataclass
from typing import Any, Literal

import aiosqlite

#: Les seules colonnes de regroupement admises ; jamais une valeur de requête.
CostColumn = Literal["ac.role", "ac.model", "pr.project_id"]


@dataclass(frozen=True)
class CostLine:
    """The cost of one role, model or project."""

    key: str
    cost_usd: float
    tokens: int
    calls: int
    avg_duration_ms: float


async def aggregate_cost(
    db: aiosqlite.Connection,
    column: CostColumn,
    where: str,
    params: tuple[Any, ...],
) -> list[CostLine]:
    """Sum cost, tokens and calls grouped by `column`, most expensive first.

    `where` is a SQL condition over the aliases `ac` (agent_calls) and `pr`
    (pipeline_runs), written by the caller; `1 = 1` selects everything.
    """
    async with db.execute(
        f"""SELECT {column} AS cle,
                   COALESCE(SUM(ac.cost_usd), 0.0) AS cost,
                   COALESCE(SUM(ac.input_tokens + ac.output_tokens
                                + ac.cache_read_tokens), 0) AS tokens,
                   COUNT(*) AS calls,
                   COALESCE(AVG(ac.duration_ms), 0.0) AS duration
            FROM agent_calls ac JOIN pipeline_runs pr ON pr.id = ac.run_id
            WHERE {where}
            GROUP BY {column} ORDER BY cost DESC""",
        params,
    ) as cursor:
        rows = await cursor.fetchall()
    return [
        CostLine(
            key=str(row["cle"]),
            cost_usd=float(row["cost"]),
            tokens=int(row["tokens"]),
            calls=int(row["calls"]),
            avg_duration_ms=float(row["duration"]),
        )
        for row in rows
    ]
