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

# Type alias: run_id → (cost_usd, input_tokens, output_tokens)
_RunCosts = dict[str, tuple[float, int, int]]


class _Scope:
    """The WHERE clauses shared by every query of one request."""

    def __init__(self, since: str, until_exc: str, project_id: str | None) -> None:
        self.since = since
        self.until_exc = until_exc
        projet = " AND pr.project_id = ?" if project_id is not None else ""
        extra: tuple[Any, ...] = (project_id,) if project_id is not None else ()
        # Les timestamps ISO (`2026-09-27T10:00:00+00:00`) trient
        # lexicographiquement comme des dates : `>= since AND < until_exc`
        # (borne exclusive = jour suivant) évite `substr()`, qui empêchait
        # SQLite d'utiliser l'index `(run_id, created_at)` même quand le
        # planificateur connaissait le `run_id` via la jointure (ticket-345).
        self.calls = f"ac.created_at >= ? AND ac.created_at < ?{projet}"
        # Les enveloppes de file (mode = 'queue' ou 'autonomous') ne sont pas
        # des runs de tickets : elles portent les événements du canal mais n'ont
        # pas d'appels agents rattachés. Les coûts et tokens ne sont pas filtrés
        # ici — ils viennent de agent_calls, qui n'ont de lignes que sur les
        # runs de tickets (ticket-263).
        # mode IS NULL : lignes antérieures à la migration, traitées comme single.
        mode_ok = " AND (pr.mode IS NULL OR pr.mode = 'single')"
        self.runs = f"pr.started_at >= ? AND pr.started_at < ?{projet}{mode_ok}"
        self.chat = "ts >= ? AND ts < ?" + (
            " AND project_id = ?" if project_id is not None else ""
        )
        self.params: tuple[Any, ...] = (since, until_exc, *extra)


async def usage_stats(
    db_path: Path | str,
    days: int,
    project_id: str | None,
    today: date | None = None,
) -> UsageStats:
    """Everything the statistics screen shows for the last `days` UTC days."""
    until_day = today or datetime.now(timezone.utc).date()
    since_day = until_day - timedelta(days=days - 1)
    since = since_day.isoformat()
    until = until_day.isoformat()
    until_exc = (until_day + timedelta(days=1)).isoformat()
    scope = _Scope(since, until_exc, project_id)

    async with aiosqlite.connect(str(db_path)) as db:
        db.row_factory = aiosqlite.Row
        # Un seul passage sur agent_calls, groupé par (day, role, model,
        # project_id, run_id). Toutes les agrégations suivantes en dérivent
        # en Python, sans relire la table (ticket-378).
        ac_buckets = await _one_pass_agent_calls(db, scope)
        run_costs = _run_costs_from_buckets(ac_buckets)
        totals = await _totals(db, scope, ac_buckets)
        daily = await _daily(db, scope, since_day, days, ac_buckets)
        per_agent = _breakdown_rows(ac_buckets, "role")
        per_model = _breakdown_rows(ac_buckets, "model")
        per_project = (
            _breakdown_rows(ac_buckets, "project_id") if project_id is None else []
        )
        quality = await _quality(db, scope)
        recent = await _recent_runs(db, scope, run_costs=run_costs)

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


async def _one_pass_agent_calls(
    db: aiosqlite.Connection, scope: _Scope
) -> list[aiosqlite.Row]:
    """Single query over agent_calls, grouped by (day, role, model, project_id, run_id).

    Remplace les 5 requêtes séparées sur agent_calls : totaux, quotidien,
    trois ventilations et le sous-SELECT de _recent_runs. Avec 50 000 lignes,
    passer de 5 scans à 1 divise le temps de calcul par ~5 (ticket-378).
    """
    return await _all(db, f"""
        SELECT substr(ac.created_at, 1, 10) AS day,
               ac.role, ac.model, pr.project_id, ac.run_id,
               SUM(ac.input_tokens)      AS tin,
               SUM(ac.output_tokens)     AS tout,
               SUM(ac.cache_read_tokens) AS tcache,
               SUM(ac.cost_usd)          AS cost,
               SUM(ac.duration_ms)       AS duration,
               COUNT(*)                  AS calls
        FROM agent_calls ac JOIN pipeline_runs pr ON pr.id = ac.run_id
        WHERE {scope.calls}
        GROUP BY day, ac.role, ac.model, pr.project_id, ac.run_id
    """, scope.params)


def _run_costs_from_buckets(ac_buckets: list[aiosqlite.Row]) -> _RunCosts:
    """(cost_usd, input_tokens, output_tokens) keyed by run_id."""
    costs: _RunCosts = {}
    for b in ac_buckets:
        run_id = str(b["run_id"])
        prev_cost, prev_tin, prev_tout = costs.get(run_id, (0.0, 0, 0))
        costs[run_id] = (
            prev_cost + float(b["cost"]),
            prev_tin + int(b["tin"]),
            prev_tout + int(b["tout"]),
        )
    return costs


async def _totals(
    db: aiosqlite.Connection, scope: _Scope, ac_buckets: list[aiosqlite.Row]
) -> UsageTotals:
    # Partie agent_calls : dérivée des buckets pré-calculés, sans requête DB.
    total_calls = total_tin = total_tout = total_tcache = total_duration = 0
    total_pipeline_cost = 0.0
    for b in ac_buckets:
        total_calls += int(b["calls"])
        total_tin += int(b["tin"])
        total_tout += int(b["tout"])
        total_tcache += int(b["tcache"])
        total_pipeline_cost += float(b["cost"])
        total_duration += int(b["duration"])
    # Parties pipeline_runs et chat_messages : tables légères.
    runs = await _one(
        db, f"SELECT COUNT(*) AS n FROM pipeline_runs pr WHERE {scope.runs}", scope.params
    )
    chat = await _one(
        db,
        f"SELECT COALESCE(SUM(cost_usd), 0.0) AS cost FROM chat_messages WHERE {scope.chat}",
        scope.params,
    )
    pipeline_cost = round(total_pipeline_cost, 10)
    chat_cost = round(float(chat["cost"]), 10)
    return UsageTotals(
        runs=int(runs["n"]), calls=total_calls,
        input_tokens=total_tin, output_tokens=total_tout,
        cache_read_tokens=total_tcache,
        pipeline_cost_usd=pipeline_cost, chat_cost_usd=chat_cost,
        cost_usd=round(pipeline_cost + chat_cost, 10),
        call_duration_ms=total_duration,
    )


async def _daily(
    db: aiosqlite.Connection, scope: _Scope, since_day: date, days: int,
    ac_buckets: list[aiosqlite.Row],
) -> list[DailyPoint]:
    points = {
        (since_day + timedelta(days=i)).isoformat(): DailyPoint(
            day=(since_day + timedelta(days=i)).isoformat()
        )
        for i in range(days)
    }
    # Partie agent_calls : dérivée des buckets, accumulation par jour.
    for b in ac_buckets:
        day_key = str(b["day"])
        if day_key in points:
            point = points[day_key]
            point.input_tokens += int(b["tin"])
            point.output_tokens += int(b["tout"])
            point.cost_usd += float(b["cost"])
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


def _breakdown_rows(
    ac_buckets: list[aiosqlite.Row], key_field: str
) -> list[BreakdownLine]:
    """Derive a breakdown from pre-computed agent_calls buckets (no DB query).

    `key_field` doit être une colonne du SELECT de _one_pass_agent_calls.
    Autorisé : 'role', 'model', 'project_id' — jamais une entrée utilisateur.
    """
    # agg: key → [cost, tokens, calls, total_duration_ms]
    agg: dict[str, list[float]] = {}
    for b in ac_buckets:
        key = str(b[key_field])
        if key not in agg:
            agg[key] = [0.0, 0.0, 0.0, 0.0]
        agg[key][0] += float(b["cost"])
        agg[key][1] += int(b["tin"]) + int(b["tout"]) + int(b["tcache"])
        agg[key][2] += int(b["calls"])
        agg[key][3] += float(b["duration"])
    return sorted(
        [
            BreakdownLine(
                key=key,
                cost_usd=round(v[0], 10),
                tokens=int(v[1]),
                calls=int(v[2]),
                avg_duration_ms=v[3] / v[2] if v[2] else 0.0,
            )
            for key, v in agg.items()
        ],
        key=lambda x: x.cost_usd,
        reverse=True,
    )


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


async def recent_runs(
    db_path: Path | str,
    days: int,
    project_id: str | None,
    *,
    limit: int,
    recherche: str | None = None,
    today: date | None = None,
) -> list[RecentRun]:
    """The latest `limit` ticket runs of the period, filtered by `recherche`.

    Serves the « Afficher plus » and the search of the recent-runs card
    (ticket-335) without recomputing the whole statistics screen.
    """
    until_day = today or datetime.now(timezone.utc).date()
    since_day = until_day - timedelta(days=days - 1)
    until_exc = (until_day + timedelta(days=1)).isoformat()
    scope = _Scope(since_day.isoformat(), until_exc, project_id)
    async with aiosqlite.connect(str(db_path)) as db:
        db.row_factory = aiosqlite.Row
        return await _recent_runs(db, scope, limit=limit, recherche=recherche)


def _motif_like(recherche: str) -> str:
    # `%` et `_` tapés dans la recherche sont des caractères, pas des jokers.
    echappe = recherche.replace("!", "!!").replace("%", "!%").replace("_", "!_")
    return f"%{echappe}%"


async def _recent_runs(
    db: aiosqlite.Connection,
    scope: _Scope,
    *,
    limit: int = RECENT_RUNS_LIMIT,
    recherche: str | None = None,
    run_costs: _RunCosts | None = None,
) -> list[RecentRun]:
    filtre = ""
    params: tuple[Any, ...] = scope.params
    if recherche:
        # LIKE ignore la casse des lettres ASCII : « BETA » trouve « beta ».
        filtre = " AND (pr.ticket_id LIKE ? ESCAPE '!' OR pr.project_id LIKE ? ESCAPE '!')"
        motif = _motif_like(recherche)
        params = (*params, motif, motif)

    if run_costs is not None:
        # Chemin rapide : coûts pré-calculés par _one_pass_agent_calls.
        # Pas de sous-SELECT sur agent_calls — aucun scan supplémentaire.
        rows = await _all(db, f"""
            SELECT pr.id, pr.project_id, pr.ticket_id, pr.started_at,
                   pr.finished_at, pr.approved, pr.final_status,
                   {_RUN_DURATION_MS} AS duration
            FROM pipeline_runs pr
            WHERE {scope.runs}{filtre}
            ORDER BY pr.started_at DESC LIMIT ?""", (*params, limit))
        return [
            RecentRun(
                id=str(r["id"]), project_id=str(r["project_id"]),
                ticket_id=str(r["ticket_id"]), started_at=str(r["started_at"]),
                finished_at=r["finished_at"],
                approved=None if r["approved"] is None else bool(r["approved"]),
                final_status=r["final_status"],
                cost_usd=round(run_costs.get(str(r["id"]), (0.0, 0, 0))[0], 10),
                input_tokens=run_costs.get(str(r["id"]), (0.0, 0, 0))[1],
                output_tokens=run_costs.get(str(r["id"]), (0.0, 0, 0))[2],
                duration_ms=None if r["duration"] is None else int(r["duration"]),
            )
            for r in rows
        ]

    # Chemin autonome (appelé depuis `recent_runs()`) : sous-SELECT limité
    # à la fenêtre temporelle pour éviter un scan complet de agent_calls.
    rows = await _all(db, f"""
        SELECT pr.id, pr.project_id, pr.ticket_id, pr.started_at, pr.finished_at,
               pr.approved, pr.final_status,
               COALESCE(c.cost, 0.0) AS cost, COALESCE(c.tin, 0) AS tin,
               COALESCE(c.tout, 0) AS tout, {_RUN_DURATION_MS} AS duration
        FROM pipeline_runs pr
        LEFT JOIN (SELECT run_id, SUM(cost_usd) AS cost, SUM(input_tokens) AS tin,
                          SUM(output_tokens) AS tout
                   FROM agent_calls
                   WHERE created_at >= ? AND created_at < ?
                   GROUP BY run_id) c ON c.run_id = pr.id
        WHERE {scope.runs}{filtre}
        ORDER BY pr.started_at DESC LIMIT ?""",
        # Le sous-SELECT apparaît avant le WHERE extérieur : ses `?` sont liés
        # en premier dans l'ordre du texte SQL.
        (scope.since, scope.until_exc, *params, limit))
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
