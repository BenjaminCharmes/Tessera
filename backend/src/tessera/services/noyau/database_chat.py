from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import aiosqlite
from pydantic import BaseModel


class ChatMessageRow(BaseModel):
    """One persisted chat turn — ticket-048."""

    role: str
    content: str
    cost_usd: float = 0.0
    ts: str


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
                datetime.now(UTC).isoformat(),
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


class ConversationSummary(BaseModel):
    """A conversation as the listing endpoint exposes it — ticket-224."""

    conversation_id: str
    title: str
    last_activity: str
    messages: list[ChatMessageRow]


def _conversation_title(messages: list[ChatMessageRow], max_len: int = 60) -> str:
    """First user message, truncated to max_len characters."""
    for msg in messages:
        if msg.role == "user":
            return msg.content[:max_len]
    return ""


async def list_conversations(
    db_path: Path | str, project_id: str
) -> list[ConversationSummary]:
    """All conversations for a project, most recent first — ticket-224."""
    async with aiosqlite.connect(str(db_path)) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT conversation_id, MAX(ts) AS last_activity
               FROM chat_messages
               WHERE project_id = ?
               GROUP BY conversation_id
               ORDER BY MAX(ts) DESC""",
            (project_id,),
        ) as cursor:
            conv_rows = await cursor.fetchall()

        if not conv_rows:
            return []

        async with db.execute(
            """SELECT conversation_id, role, content, cost_usd, ts
               FROM chat_messages
               WHERE project_id = ?
               ORDER BY id""",
            (project_id,),
        ) as cursor:
            msg_rows = await cursor.fetchall()

    messages_by_conv: dict[str, list[ChatMessageRow]] = {}
    for row in msg_rows:
        conv_id = str(row["conversation_id"])
        if conv_id not in messages_by_conv:
            messages_by_conv[conv_id] = []
        messages_by_conv[conv_id].append(
            ChatMessageRow(
                role=str(row["role"]),
                content=str(row["content"]),
                cost_usd=float(row["cost_usd"]),
                ts=str(row["ts"]),
            )
        )

    return [
        ConversationSummary(
            conversation_id=str(row["conversation_id"]),
            title=_conversation_title(
                messages_by_conv.get(str(row["conversation_id"]), [])
            ),
            last_activity=str(row["last_activity"]),
            messages=messages_by_conv.get(str(row["conversation_id"]), []),
        )
        for row in conv_rows
    ]
