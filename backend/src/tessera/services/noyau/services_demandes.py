"""L'intention « les services de ce projet doivent tourner » — ticket-890, ADR-082.

Seule l'intention se persiste : les processus restent des enfants du backend
(ADR-042) et meurent avec lui.
"""
from datetime import UTC, datetime
from pathlib import Path

import aiosqlite


async def demander(db_path: Path | str, project_id: str) -> None:
    """Record that the project's services should run (upsert)."""
    async with aiosqlite.connect(str(db_path)) as db:
        await db.execute(
            "INSERT INTO services_demandes (project_id, demande_le) VALUES (?, ?) "
            "ON CONFLICT(project_id) DO UPDATE SET demande_le = excluded.demande_le",
            (project_id, datetime.now(UTC).isoformat()),
        )
        await db.commit()


async def retirer(db_path: Path | str, project_id: str) -> None:
    """Forget the intention for a project; a no-op if absent."""
    async with aiosqlite.connect(str(db_path)) as db:
        await db.execute(
            "DELETE FROM services_demandes WHERE project_id = ?", (project_id,)
        )
        await db.commit()


async def lister(db_path: Path | str) -> list[str]:
    """Return the project ids whose services were requested, oldest first."""
    async with aiosqlite.connect(str(db_path)) as db:
        async with db.execute(
            "SELECT project_id FROM services_demandes ORDER BY demande_le, project_id"
        ) as curseur:
            return [ligne[0] async for ligne in curseur]
