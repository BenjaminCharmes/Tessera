"""SHA bound to an approval — ticket-492.

`approved_sha` is the head of the run's branch when the reviewer and the
validator approved it; `pushed_sha` is the head that left for the remote. Both
live on the `pipeline_runs` row of the run, so the merge can be checked against
what was read, long after the run task is gone.
"""
from pathlib import Path

import aiosqlite


async def noter_approbation(db_path: Path | str, run_id: str, sha: str) -> None:
    """Record the commit the run was approved on."""
    await _ecrire(db_path, "approved_sha", run_id, sha)


async def noter_poussee(db_path: Path | str, run_id: str, sha: str) -> None:
    """Record the commit pushed for the run's pull request."""
    await _ecrire(db_path, "pushed_sha", run_id, sha)


async def sha_pousse_du_ticket(
    db_path: Path | str, project_id: str, ticket_id: str
) -> str | None:
    """The `pushed_sha` of the latest run of the ticket that pushed one."""
    async with aiosqlite.connect(str(db_path)) as db:
        async with db.execute(
            "SELECT pushed_sha FROM pipeline_runs"
            " WHERE project_id=? AND ticket_id=? AND pushed_sha IS NOT NULL"
            " ORDER BY started_at DESC, rowid DESC LIMIT 1",
            (project_id, ticket_id),
        ) as cursor:
            ligne = await cursor.fetchone()
    return str(ligne[0]) if ligne else None


async def _ecrire(
    db_path: Path | str, colonne: str, run_id: str, sha: str
) -> None:
    # `colonne` vient de ce module (deux constantes), jamais d'une entrée.
    async with aiosqlite.connect(str(db_path)) as db:
        await db.execute(
            f"UPDATE pipeline_runs SET {colonne}=? WHERE id=?", (sha, run_id)
        )
        await db.commit()
