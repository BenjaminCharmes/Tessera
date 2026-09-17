from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite
from pydantic import BaseModel

_CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id           TEXT PRIMARY KEY,
    project_id   TEXT NOT NULL,
    ticket_id    TEXT NOT NULL,
    started_at   TEXT NOT NULL,
    finished_at  TEXT,
    rounds       INTEGER,
    approved     INTEGER,
    final_status TEXT
);

CREATE TABLE IF NOT EXISTS agent_events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id     TEXT NOT NULL REFERENCES pipeline_runs(id),
    type       TEXT NOT NULL,
    agent      TEXT,
    data_json  TEXT,
    ts         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_calls (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id            TEXT NOT NULL REFERENCES pipeline_runs(id),
    ticket_id         TEXT NOT NULL,
    role              TEXT NOT NULL,
    model             TEXT NOT NULL,
    input_tokens      INTEGER NOT NULL DEFAULT 0,
    output_tokens     INTEGER NOT NULL DEFAULT 0,
    cache_read_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd          REAL NOT NULL DEFAULT 0.0,
    duration_ms       INTEGER NOT NULL DEFAULT 0,
    created_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id    TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    role          TEXT NOT NULL,
    content       TEXT NOT NULL,
    cost_usd      REAL NOT NULL DEFAULT 0.0,
    ts            TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_conversation
    ON chat_messages (project_id, conversation_id, id);
"""


class ChatMessageRow(BaseModel):
    """One persisted chat turn — ticket-048."""

    role: str
    content: str
    cost_usd: float = 0.0
    ts: str


class PipelineRunSummary(BaseModel):
    id: str
    ticket_id: str
    started_at: str
    finished_at: str | None = None
    rounds: int | None = None
    approved: bool | None = None
    final_status: str | None = None
    total_cost_usd: float = 0.0


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


async def init_db(db_path: Path | str) -> None:
    async with aiosqlite.connect(str(db_path)) as db:
        await db.executescript(_CREATE_TABLES)
        await db.execute("PRAGMA journal_mode=WAL")
        await db.commit()


async def create_run(db_path: Path | str, project_id: str, ticket_id: str) -> str:
    run_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(str(db_path)) as db:
        await db.execute(
            "INSERT INTO pipeline_runs (id, project_id, ticket_id, started_at) VALUES (?,?,?,?)",
            (run_id, project_id, ticket_id, started_at),
        )
        await db.commit()
    return run_id


async def finish_run(
    db_path: Path | str,
    run_id: str,
    rounds: int,
    approved: bool,
    final_status: str,
) -> None:
    finished_at = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(str(db_path)) as db:
        await db.execute(
            """UPDATE pipeline_runs
               SET finished_at=?, rounds=?, approved=?, final_status=?
               WHERE id=?""",
            (finished_at, rounds, int(approved), final_status, run_id),
        )
        await db.commit()


async def save_event(
    db_path: Path | str,
    run_id: str,
    event_type: str,
    agent: str | None,
    data: dict[str, Any],
    timestamp: str,
) -> None:
    async with aiosqlite.connect(str(db_path)) as db:
        await db.execute(
            "INSERT INTO agent_events (run_id, type, agent, data_json, ts) VALUES (?,?,?,?,?)",
            (run_id, event_type, agent, json.dumps(data), timestamp),
        )
        await db.commit()


async def save_agent_call(
    db_path: Path | str,
    run_id: str,
    ticket_id: str,
    role: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int,
    cost_usd: float,
    duration_ms: int,
) -> None:
    created_at = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(str(db_path)) as db:
        await db.execute(
            """INSERT INTO agent_calls
               (run_id, ticket_id, role, model, input_tokens, output_tokens,
                cache_read_tokens, cost_usd, duration_ms, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (run_id, ticket_id, role, model, input_tokens, output_tokens,
             cache_read_tokens, cost_usd, duration_ms, created_at),
        )
        await db.commit()


async def list_runs(
    db_path: Path | str,
    project_id: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    async with aiosqlite.connect(str(db_path)) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT pr.id, pr.ticket_id, pr.started_at, pr.finished_at,
                      pr.rounds, pr.approved, pr.final_status,
                      COALESCE(SUM(ac.cost_usd), 0.0) as total_cost_usd
               FROM pipeline_runs pr
               LEFT JOIN agent_calls ac ON ac.run_id = pr.id
               WHERE pr.project_id=?
               GROUP BY pr.id
               -- `rowid` départage à égalité d'horodatage. Deux runs créés
               -- dans la même milliseconde laissaient SQLite trancher seul :
               -- l'historique s'affichait alors dans un ordre variable, et le
               -- test d'ordre échouait une fois sur quelques dizaines.
               ORDER BY pr.started_at DESC, pr.rowid DESC
               LIMIT ?""",
            (project_id, limit),
        ) as cursor:
            rows = await cursor.fetchall()
    return [
        {
            "id": row["id"],
            "ticket_id": row["ticket_id"],
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "rounds": row["rounds"],
            "approved": bool(row["approved"]) if row["approved"] is not None else None,
            "final_status": row["final_status"],
            "total_cost_usd": float(row["total_cost_usd"]),
        }
        for row in rows
    ]


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


# ------------------------------------------------------------------
# Chat (ticket-048)
# ------------------------------------------------------------------


async def save_chat_message(
    db_path: Path | str,
    project_id: str,
    conversation_id: str,
    role: str,
    content: str,
    cost_usd: float = 0.0,
) -> None:
    """Append one turn to a conversation, so it survives a page reload."""
    async with aiosqlite.connect(str(db_path)) as db:
        await db.execute(
            "INSERT INTO chat_messages "
            "(project_id, conversation_id, role, content, cost_usd, ts) "
            "VALUES (?,?,?,?,?,?)",
            (
                project_id,
                conversation_id,
                role,
                content,
                cost_usd,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        await db.commit()


async def list_chat_messages(
    db_path: Path | str, project_id: str, conversation_id: str
) -> list[ChatMessageRow]:
    """Every turn of one conversation, oldest first."""
    async with aiosqlite.connect(str(db_path)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT role, content, cost_usd, ts FROM chat_messages "
            "WHERE project_id = ? AND conversation_id = ? ORDER BY id",
            (project_id, conversation_id),
        )
        rows = await cursor.fetchall()
    return [
        ChatMessageRow(
            role=str(r["role"]),
            content=str(r["content"]),
            cost_usd=float(r["cost_usd"]),
            ts=str(r["ts"]),
        )
        for r in rows
    ]


async def conversation_cost_usd(
    db_path: Path | str, project_id: str, conversation_id: str
) -> float:
    """Total spent on one conversation.

    `llm_max_budget_usd` bounds a single call, not a conversation: without a
    running total, a long discussion burns the subscription quota with nothing
    surfacing it.
    """
    async with aiosqlite.connect(str(db_path)) as db:
        cursor = await db.execute(
            "SELECT COALESCE(SUM(cost_usd), 0.0) FROM chat_messages "
            "WHERE project_id = ? AND conversation_id = ?",
            (project_id, conversation_id),
        )
        row = await cursor.fetchone()
    return round(float(row[0]) if row else 0.0, 10)


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
    coûte vibe-ide ce mois-ci » n'avait aucune réponse, chaque endpoint étant
    borné à un projet.
    """
    filtre = "WHERE pr.project_id = ?" if project_id is not None else ""
    params: tuple[Any, ...] = (project_id,) if project_id is not None else ()

    async with aiosqlite.connect(str(db_path)) as db:
        db.row_factory = aiosqlite.Row

        async def _agrege(colonne: str) -> list[dict[str, Any]]:
            async with db.execute(
                f"""SELECT ac.{colonne} AS cle,
                           COALESCE(SUM(ac.cost_usd), 0.0) AS total_cost_usd,
                           COALESCE(SUM(ac.input_tokens + ac.output_tokens
                                        + ac.cache_read_tokens), 0) AS total_tokens,
                           COUNT(*) AS call_count
                    FROM agent_calls ac
                    JOIN pipeline_runs pr ON pr.id = ac.run_id
                    {filtre}
                    GROUP BY ac.{colonne}
                    ORDER BY total_cost_usd DESC""",
                params,
            ) as cursor:
                lignes = await cursor.fetchall()
            return [
                {
                    colonne: row["cle"],
                    "total_cost_usd": float(row["total_cost_usd"]),
                    "total_tokens": int(row["total_tokens"]),
                    "call_count": int(row["call_count"]),
                }
                for row in lignes
            ]

        per_agent = await _agrege("role")
        per_model = await _agrege("model")

    return {
        "project_id": project_id,
        "total_cost_usd": round(sum(a["total_cost_usd"] for a in per_agent), 10),
        "per_agent": per_agent,
        "per_model": per_model,
    }
