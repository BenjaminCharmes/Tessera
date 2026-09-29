from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite
from pydantic import BaseModel

from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

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
    arret: str | None = None


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


#: Les évolutions du schéma, dans l'ordre, une entrée par changement
#: (ticket-086). L'index d'une migration + 1 est le `user_version` qu'elle
#: fait atteindre ; `PRAGMA user_version` dit donc lesquelles ont déjà tourné.
#:
#: **`_CREATE_TABLES` ne bouge plus.** Il décrit le schéma d'origine ; toute
#: évolution s'ajoute ici. Le modifier ferait diverger une base neuve d'une
#: base migrée, et l'écart ne se verrait qu'à l'usage, sur la base de
#: quelqu'un. Un test compare les deux.
_MIGRATIONS: list[str] = [
    # 1 — ticket-188 : le provider qui a répondu, pour que la ventilation des
    # coûts dise ce qui a tourné quand un repli a servi.
    "ALTER TABLE agent_calls ADD COLUMN provider TEXT NOT NULL DEFAULT '';",
    # 2 — ticket-218 : la cause d'un blocage, pour que l'activité du ticket
    # l'expose sans fouiller les événements.
    "ALTER TABLE pipeline_runs ADD COLUMN arret TEXT;",
]


def version_du_schema() -> int:
    """Le numéro de version que le code attend de la base."""
    return len(_MIGRATIONS)


async def init_db(db_path: Path | str) -> None:
    """Crée le schéma s'il manque, puis applique les migrations en retard.

    Sans numéro de version, `CREATE TABLE IF NOT EXISTS` créait ce qui
    manquait et ignorait tout le reste : une colonne ajoutée un jour n'aurait
    jamais atteint une base existante, en silence. L'historique des runs et
    des coûts n'est pas reconstructible — il ne se recrée pas, il se migre.
    """
    async with aiosqlite.connect(str(db_path)) as db:
        await db.executescript(_CREATE_TABLES)

        curseur = await db.execute("PRAGMA user_version")
        ligne = await curseur.fetchone()
        version = int(ligne[0]) if ligne else 0

        for numero, migration in enumerate(_MIGRATIONS[version:], start=version + 1):
            await db.executescript(migration)
            # `user_version` n'accepte pas de paramètre lié ; `numero` est un
            # entier issu d'`enumerate`, jamais d'une entrée utilisateur.
            await db.execute(f"PRAGMA user_version = {numero}")
            _logger.info("migration_appliquee", extra={"version": numero})

        if version > len(_MIGRATIONS):
            # Base écrite par une version plus récente de l'application — le
            # cas d'un aller-retour entre deux machines. Ne rien faire vaut
            # mieux que réécrire un schéma qu'on ne connaît pas.
            _logger.warning(
                "base_plus_recente_que_le_code",
                extra={"base": version, "code": len(_MIGRATIONS)},
            )

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
    arret: str | None = None,
) -> None:
    finished_at = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(str(db_path)) as db:
        await db.execute(
            """UPDATE pipeline_runs
               SET finished_at=?, rounds=?, approved=?, final_status=?, arret=?
               WHERE id=?""",
            (finished_at, rounds, int(approved), final_status, arret, run_id),
        )
        await db.commit()


#: La cause écrite sur un run que le processus a laissé derrière lui.
CAUSE_RUN_ORPHELIN = "backend restarted: the run's process is gone"


async def solder_les_runs_orphelins(db_path: Path | str) -> list[str]:
    """Settles every run left without `finished_at` — ticket-177.

    Un backend local n'a qu'un processus (ADR-038) : au démarrage, un run
    encore « en cours » en base est celui d'un processus qui n'est plus là.
    Un `kill` n'exécute aucun `finally`, donc ni ADR-037 ni le commit de fin
    de run n'ont eu lieu. On solde en `blocked`, jamais en approuvé, en
    laissant intacts les événements et les coûts déjà enregistrés, et on
    écrit la cause comme un événement `error`, pour que l'historique la
    montre. Le jour où deux backends partageraient une base, cette hypothèse
    tomberait : elle est ici, pas supposée ailleurs.
    """
    maintenant = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(str(db_path)) as db:
        async with db.execute(
            "SELECT id, rounds FROM pipeline_runs WHERE finished_at IS NULL"
        ) as cursor:
            orphelins = await cursor.fetchall()
        for run_id, rounds in orphelins:
            await db.execute(
                "INSERT INTO agent_events (run_id, type, agent, data_json, ts) VALUES (?,?,?,?,?)",
                (
                    run_id, "error", None,
                    json.dumps({"reason": "interrupted", "detail": CAUSE_RUN_ORPHELIN}),
                    maintenant,
                ),
            )
            await db.execute(
                """UPDATE pipeline_runs
                   SET finished_at=?, rounds=?, approved=0, final_status='blocked',
                       arret=?
                   WHERE id=?""",
                (maintenant, int(rounds or 0), CAUSE_RUN_ORPHELIN, run_id),
            )
        await db.commit()
    return [str(run_id) for run_id, _ in orphelins]


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
    provider: str = "",
) -> None:
    created_at = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(str(db_path)) as db:
        await db.execute(
            """INSERT INTO agent_calls
               (run_id, ticket_id, role, model, input_tokens, output_tokens,
                cache_read_tokens, cost_usd, duration_ms, created_at, provider)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (run_id, ticket_id, role, model, input_tokens, output_tokens,
             cache_read_tokens, cost_usd, duration_ms, created_at, provider),
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
                      pr.rounds, pr.approved, pr.final_status, pr.arret,
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
            "arret": row["arret"],
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
    coûte Tessera ce mois-ci » n'avait aucune réponse, chaque endpoint étant
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

        # Ventiler par projet quand on en regarde un seul n'apprendrait rien :
        # cette clé ne se remplit que sur la vue d'ensemble (ticket-082).
        per_project: list[dict[str, Any]] = []
        if project_id is None:
            async with db.execute(
                """SELECT pr.project_id AS cle,
                          COALESCE(SUM(ac.cost_usd), 0.0) AS total_cost_usd,
                          COALESCE(SUM(ac.input_tokens + ac.output_tokens
                                       + ac.cache_read_tokens), 0) AS total_tokens,
                          COUNT(ac.id) AS call_count
                   FROM pipeline_runs pr
                   JOIN agent_calls ac ON ac.run_id = pr.id
                   GROUP BY pr.project_id
                   ORDER BY total_cost_usd DESC"""
            ) as cursor:
                lignes = await cursor.fetchall()
            per_project = [
                {
                    "project_id": row["cle"],
                    "total_cost_usd": float(row["total_cost_usd"]),
                    "total_tokens": int(row["total_tokens"]),
                    "call_count": int(row["call_count"]),
                }
                for row in lignes
            ]

    return {
        "project_id": project_id,
        "total_cost_usd": round(sum(a["total_cost_usd"] for a in per_agent), 10),
        "per_agent": per_agent,
        "per_model": per_model,
        "per_project": per_project,
    }
