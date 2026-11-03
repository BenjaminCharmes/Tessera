"""Écriture d'un appel d'agent dans `agent_calls`."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import aiosqlite


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
    cache_creation_tokens: int = 0,
) -> None:
    """Persist one LLM call; `cache_creation_tokens` is kept apart from the input."""
    created_at = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(str(db_path)) as db:
        await db.execute(
            """INSERT INTO agent_calls
               (run_id, ticket_id, role, model, input_tokens, output_tokens,
                cache_read_tokens, cost_usd, duration_ms, created_at, provider,
                cache_creation_tokens)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (run_id, ticket_id, role, model, input_tokens, output_tokens,
             cache_read_tokens, cost_usd, duration_ms, created_at, provider,
             cache_creation_tokens),
        )
        await db.commit()
