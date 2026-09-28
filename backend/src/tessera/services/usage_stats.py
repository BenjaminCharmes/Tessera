"""Usage statistics over a period — ticket-201.

`get_usage_breakdown` dit où part la dépense, sans dimension de temps : on n'y
voit ni tendance, ni pic, ni taux d'approbation qui baisse. Ce module rend en
une réponse ce qu'un tableau de bord affiche pour une période.

Les jours sont des jours **UTC** : c'est ainsi que `created_at` et
`started_at` sont stockés, et convertir ici supposerait un fuseau que le
backend ne connaît pas. `agent_calls` n'a pas de `project_id` : le projet d'un
appel passe par son run.
"""
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import aiosqlite

from tessera.models.usage import (
    BreakdownLine,
    DailyPoint,
    RecentRun,
    RunQuality,
    StatusCount,
    UsageStats,
    UsageTotals,
)

#: Les périodes que l'écran propose ; l'endpoint refuse les autres.
PERIODS = (7, 30, 90)
RECENT_RUNS_LIMIT = 10

_RUN_DURATION_MS = (
    "CAST(ROUND((julianday(pr.finished_at) - julianday(pr.started_at)) * 86400000)"
    " AS INTEGER)"
)


class _Scope:
    """The WHERE clauses shared by every query of one request."""

    def __init__(self, since: str, until: str, project_id: str | None) -> None:
        projet = " AND pr.project_id = ?" if project_id is not None else ""
        extra: tuple[Any, ...] = (project_id,) if project_id is not None else ()
        self.calls = f"substr(ac.created_at, 1, 10) BETWEEN ? AND ?{projet}"
        self.runs = f"substr(pr.started_at, 1, 10) BETWEEN ? AND ?{projet}"
        self.chat = "substr(ts, 1, 10) BETWEEN ? AND ?" + (
            " AND project_id = ?" if project_id is not None else ""
        )
        self.params: tuple[Any, ...] = (since, until, *extra)


async def usage_stats(
    db_path: Path | str,
    days: int,
    project_id: str | None,
    today: date | None = None,
) -> UsageStats:
    """Everything the statistics screen shows for the last `days` UTC days."""
    until_day = today or datetime.now(timezone.utc).date()
    since_day = until_day - timedelta(days=days - 1)
    since, until = since_day.isoformat(), until_day.isoformat()
    scope = _Scope(since, until, project_id)

    async with aiosqlite.connect(str(db_path)) as db:
        db.row_factory = aiosqlite.Row
        totals = await _totals(db, scope)
        daily = await _daily(db, scope, since_day, days)
        per_agent = await _breakdown(db, scope, "ac.role")
        per_model = await _breakdown(db, scope, "ac.model")
        per_project = (
            await _breakdown(db, scope, "pr.project_id") if project_id is None else []
        )
        quality = await _quality(db, scope)
        recent = await _recent_runs(db, scope)

    return UsageStats(
        days=days, project_id=project_id, since=since, until=until,
        totals=totals, daily=daily, per_agent=per_agent, per_model=per_model,
        per_project=per_project, quality=quality, recent_runs=recent,
    )


async def _one(db: aiosqlite.Connection, sql: str, params: tuple[Any, ...]) -> aiosqlite.Row:
    async with db.execute(sql, params) as cursor:
        row = await cursor.fetchone()
    assert row is not None  # un agrégat sans GROUP BY rend toujours une ligne
    return row


async def _all(
    db: aiosqlite.Connection, sql: str, params: tuple[Any, ...]
) -> list[aiosqlite.Row]:
    async with db.execute(sql, params) as cursor:
        return list(await cursor.fetchall())


async def _totals(db: aiosqlite.Connection, scope: _Scope) -> UsageTotals:
    calls = await _one(db, f"""
        SELECT COUNT(*) AS calls,
               COALESCE(SUM(ac.input_tokens), 0) AS tin,
               COALESCE(SUM(ac.output_tokens), 0) AS tout,
               COALESCE(SUM(ac.cache_read_tokens), 0) AS tcache,
               COALESCE(SUM(ac.cost_usd), 0.0) AS cost,
               COALESCE(SUM(ac.duration_ms), 0) AS duration
        FROM agent_calls ac JOIN pipeline_runs pr ON pr.id = ac.run_id
        WHERE {scope.calls}""", scope.params)
    runs = await _one(
        db, f"SELECT COUNT(*) AS n FROM pipeline_runs pr WHERE {scope.runs}", scope.params
    )
    chat = await _one(
        db,
        f"SELECT COALESCE(SUM(cost_usd), 0.0) AS cost FROM chat_messages WHERE {scope.chat}",
        scope.params,
    )
    pipeline_cost = round(float(calls["cost"]), 10)
    chat_cost = round(float(chat["cost"]), 10)
    return UsageTotals(
        runs=int(runs["n"]), calls=int(calls["calls"]),
        input_tokens=int(calls["tin"]), output_tokens=int(calls["tout"]),
        cache_read_tokens=int(calls["tcache"]),
        pipeline_cost_usd=pipeline_cost, chat_cost_usd=chat_cost,
        cost_usd=round(pipeline_cost + chat_cost, 10),
        call_duration_ms=int(calls["duration"]),
    )


async def _daily(
    db: aiosqlite.Connection, scope: _Scope, since_day: date, days: int
) -> list[DailyPoint]:
    points = {
        (since_day + timedelta(days=i)).isoformat(): DailyPoint(
            day=(since_day + timedelta(days=i)).isoformat()
        )
        for i in range(days)
    }
    for row in await _all(db, f"""
            SELECT substr(ac.created_at, 1, 10) AS day,
                   SUM(ac.input_tokens) AS tin, SUM(ac.output_tokens) AS tout,
                   SUM(ac.cost_usd) AS cost
            FROM agent_calls ac JOIN pipeline_runs pr ON pr.id = ac.run_id
            WHERE {scope.calls} GROUP BY day""", scope.params):
        point = points[str(row["day"])]
        point.input_tokens = int(row["tin"])
        point.output_tokens = int(row["tout"])
        point.cost_usd += float(row["cost"])
    for row in await _all(db, f"""
            SELECT substr(pr.started_at, 1, 10) AS day, COUNT(*) AS n
            FROM pipeline_runs pr WHERE {scope.runs} GROUP BY day""", scope.params):
        points[str(row["day"])].runs = int(row["n"])
    for row in await _all(db, f"""
            SELECT substr(ts, 1, 10) AS day, SUM(cost_usd) AS cost
            FROM chat_messages WHERE {scope.chat} GROUP BY day""", scope.params):
        points[str(row["day"])].cost_usd += float(row["cost"])
    for point in points.values():
        point.cost_usd = round(point.cost_usd, 10)
    return list(points.values())


async def _breakdown(
    db: aiosqlite.Connection, scope: _Scope, column: str
) -> list[BreakdownLine]:
    # `column` vient d'une liste fermée dans `usage_stats`, jamais de la requête.
    rows = await _all(db, f"""
        SELECT {column} AS cle,
               SUM(ac.cost_usd) AS cost,
               SUM(ac.input_tokens + ac.output_tokens + ac.cache_read_tokens) AS tokens,
               COUNT(*) AS calls,
               AVG(ac.duration_ms) AS duration
        FROM agent_calls ac JOIN pipeline_runs pr ON pr.id = ac.run_id
        WHERE {scope.calls}
        GROUP BY {column} ORDER BY cost DESC""", scope.params)
    return [
        BreakdownLine(
            key=str(r["cle"]), cost_usd=round(float(r["cost"]), 10),
            tokens=int(r["tokens"]), calls=int(r["calls"]),
            avg_duration_ms=float(r["duration"]),
        )
        for r in rows
    ]


async def _quality(db: aiosqlite.Connection, scope: _Scope) -> RunQuality:
    finished = f"{scope.runs} AND pr.finished_at IS NOT NULL"
    row = await _one(db, f"""
        SELECT COUNT(*) AS n, SUM(COALESCE(pr.approved, 0)) AS ok,
               AVG(pr.rounds) AS rounds, AVG({_RUN_DURATION_MS}) AS duration
        FROM pipeline_runs pr WHERE {finished}""", scope.params)
    statuses = await _all(db, f"""
        SELECT COALESCE(pr.final_status, 'unknown') AS status, COUNT(*) AS n
        FROM pipeline_runs pr WHERE {finished}
        GROUP BY status ORDER BY n DESC""", scope.params)
    n = int(row["n"])
    return RunQuality(
        finished_runs=n,
        approval_rate=(int(row["ok"]) / n) if n else None,
        avg_rounds=float(row["rounds"]) if row["rounds"] is not None else None,
        avg_run_duration_ms=float(row["duration"]) if row["duration"] is not None else None,
        by_status=[StatusCount(status=str(s["status"]), count=int(s["n"])) for s in statuses],
    )


async def _recent_runs(db: aiosqlite.Connection, scope: _Scope) -> list[RecentRun]:
    rows = await _all(db, f"""
        SELECT pr.id, pr.project_id, pr.ticket_id, pr.started_at, pr.finished_at,
               pr.approved, pr.final_status,
               COALESCE(c.cost, 0.0) AS cost, COALESCE(c.tin, 0) AS tin,
               COALESCE(c.tout, 0) AS tout, {_RUN_DURATION_MS} AS duration
        FROM pipeline_runs pr
        LEFT JOIN (SELECT run_id, SUM(cost_usd) AS cost, SUM(input_tokens) AS tin,
                          SUM(output_tokens) AS tout
                   FROM agent_calls GROUP BY run_id) c ON c.run_id = pr.id
        WHERE {scope.runs}
        ORDER BY pr.started_at DESC LIMIT {RECENT_RUNS_LIMIT}""", scope.params)
    return [
        RecentRun(
            id=str(r["id"]), project_id=str(r["project_id"]), ticket_id=str(r["ticket_id"]),
            started_at=str(r["started_at"]), finished_at=r["finished_at"],
            approved=None if r["approved"] is None else bool(r["approved"]),
            final_status=r["final_status"],
            cost_usd=round(float(r["cost"]), 10), input_tokens=int(r["tin"]),
            output_tokens=int(r["tout"]),
            duration_ms=None if r["duration"] is None else int(r["duration"]),
        )
        for r in rows
    ]
