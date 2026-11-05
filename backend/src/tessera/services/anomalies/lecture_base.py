"""Read-only access to the history database — ticket-835 (ADR-078).

Le détecteur ne peut rien écrire : la base s'ouvre en `mode=ro`, et SQLite
refuse alors tout `INSERT`, quoi que fasse l'appelant.
"""
from pathlib import Path

import aiosqlite


def ouvrir_en_lecture(db_path: Path | str) -> aiosqlite.Connection:
    """Open `db_path` read-only; use as `async with ouvrir_en_lecture(p) as db`."""
    uri = Path(db_path).resolve().as_uri() + "?mode=ro"
    return aiosqlite.connect(uri, uri=True)
