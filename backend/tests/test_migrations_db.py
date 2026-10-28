"""Le schéma SQLite évolue sans perdre l'historique — ticket-086."""
import sqlite3
from pathlib import Path

import pytest

from tessera.services import database
from tessera.services.database import init_db, version_du_schema


def _version(db_path: Path) -> int:
    c = sqlite3.connect(str(db_path))
    try:
        return int(c.execute("PRAGMA user_version").fetchone()[0])
    finally:
        c.close()


async def test_une_base_neuve_est_a_la_derniere_version(tmp_path: Path) -> None:
    db = tmp_path / "tessera.db"

    await init_db(db)

    assert _version(db) == version_du_schema()


async def test_une_base_existante_est_migree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Le cas qui compte : la base de l'utilisateur, créée avant l'existence
    # des migrations. Sans numéro de version, une colonne ajoutée un jour ne
    # serait jamais vue — silencieusement.
    db = tmp_path / "tessera.db"
    await init_db(db)

    monkeypatch.setattr(
        database,
        "_MIGRATIONS",
        [*database._MIGRATIONS, "ALTER TABLE pipeline_runs ADD COLUMN essai TEXT"],
    )

    await init_db(db)

    colonnes = {
        r[1]
        for r in sqlite3.connect(str(db)).execute("PRAGMA table_info(pipeline_runs)")
    }
    assert "essai" in colonnes
    assert _version(db) == version_du_schema()


async def test_une_migration_ne_s_applique_pas_deux_fois(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # `ALTER TABLE ADD COLUMN` échoue si la colonne existe : rejouer une
    # migration déjà passée casserait le démarrage de l'application.
    db = tmp_path / "tessera.db"
    await init_db(db)
    monkeypatch.setattr(
        database,
        "_MIGRATIONS",
        [*database._MIGRATIONS, "ALTER TABLE pipeline_runs ADD COLUMN essai TEXT"],
    )
    await init_db(db)

    await init_db(db)  # ne doit pas lever

    assert _version(db) == version_du_schema()


async def test_les_donnees_survivent_a_une_migration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "tessera.db"
    await init_db(db)
    run_id = await database.create_run(db, "p", "ticket-001")

    monkeypatch.setattr(
        database,
        "_MIGRATIONS",
        [*database._MIGRATIONS, "ALTER TABLE pipeline_runs ADD COLUMN essai TEXT"],
    )
    await init_db(db)

    restants = sqlite3.connect(str(db)).execute(
        "select id from pipeline_runs"
    ).fetchall()
    assert restants == [(run_id,)]


async def test_cache_creation_tokens_column_is_added_with_zero(tmp_path: Path) -> None:
    # Une base d'avant le ticket-604 : schéma d'origine, une ligne d'appel.
    # La migration ajoute la colonne sans perdre la ligne, qui vaut 0.
    db = tmp_path / "ancienne.db"
    c = sqlite3.connect(str(db))
    c.executescript(database._CREATE_TABLES)
    c.execute(
        "INSERT INTO agent_calls (run_id, ticket_id, role, model, input_tokens, "
        "output_tokens, cache_read_tokens, cost_usd, duration_ms, created_at) "
        "VALUES ('r', 't', 'codeur', 'm', 10, 5, 3, 0.1, 1, '2026-01-01')"
    )
    c.commit()
    c.close()

    await init_db(db)

    lignes = sqlite3.connect(str(db)).execute(
        "SELECT run_id, input_tokens, cache_creation_tokens FROM agent_calls"
    ).fetchall()
    assert lignes == [("r", 10, 0)]


async def test_le_schema_de_base_ne_bouge_plus(tmp_path: Path) -> None:
    # `_CREATE_TABLES` décrit le schéma **d'origine**. Toute évolution passe
    # par une migration : le modifier ferait diverger une base neuve d'une
    # base migrée, et la différence ne se verrait qu'en production.
    neuve = tmp_path / "neuve.db"
    await init_db(neuve)

    migree = tmp_path / "migree.db"
    c = sqlite3.connect(str(migree))
    c.executescript(database._CREATE_TABLES)
    c.commit()
    c.close()
    await init_db(migree)

    def _schema(p: Path) -> set[str]:
        return {
            str(r[0])
            for r in sqlite3.connect(str(p)).execute(
                "select sql from sqlite_master where sql is not null"
            )
        }

    assert _schema(neuve) == _schema(migree)
