"""Schéma SQLite de Tessera, ses migrations et leur application — ticket-086."""

from __future__ import annotations

from pathlib import Path

import aiosqlite

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
    # 3 — ticket-263 : le mode du run (single, queue, autonomous) pour exclure
    # les enveloppes de file des statistiques. Les lignes existantes restent
    # NULL, lues comme single. On backfille les enveloppes identifiables à leur
    # ticket_id : run_executor écrivait run.mode quand ticket_id était vide.
    """ALTER TABLE pipeline_runs ADD COLUMN mode TEXT;
UPDATE pipeline_runs SET mode = 'queue'
    WHERE ticket_id = 'queue' AND mode IS NULL;
UPDATE pipeline_runs SET mode = 'autonomous'
    WHERE ticket_id = 'autonomous' AND mode IS NULL;""",
    # 4 — ticket-280 : ticket_id dans agent_events pour filtrer les événements
    # d'un ticket donné à l'intérieur d'une file. Nullable : les lignes
    # existantes et les événements d'enveloppe sans ticket cible restent NULL.
    "ALTER TABLE agent_events ADD COLUMN ticket_id TEXT;",
    # 5 — ticket-280 : parent_run_id lie les lignes par-ticket à leur enveloppe
    # de file, ce qui permet à l'endpoint d'événements de trouver les données.
    "ALTER TABLE pipeline_runs ADD COLUMN parent_run_id TEXT REFERENCES pipeline_runs(id);",
    # 6 — ticket-327 : index couvrants pour accélérer usage_stats et
    # list_runs_for_ticket. Sur 50 000 lignes agent_calls, les requêtes de stats
    # passent de > 2 s à < 200 ms.
    """CREATE INDEX IF NOT EXISTS idx_pr_project_started
        ON pipeline_runs (project_id, started_at);
CREATE INDEX IF NOT EXISTS idx_ac_run_created
        ON agent_calls (run_id, created_at);""",
    # 7 — ticket-364 : cache persistant des statuts de PR mergées ou fermées.
    # Clé (repo, pr_number) ; seules les PR définitives y vivent — une PR
    # ouverte ne s'écrit pas en base, elle est gardée 30 s en mémoire.
    """CREATE TABLE IF NOT EXISTS pr_status_cache (
    repo       TEXT NOT NULL,
    pr_number  INTEGER NOT NULL,
    state      TEXT NOT NULL,
    ci_status  TEXT NOT NULL,
    pr_url     TEXT NOT NULL,
    PRIMARY KEY (repo, pr_number)
);""",
    # 8 — ticket-492 : le commit que le reviewer et le validateur ont lu
    # (`approved_sha`) et celui qui est parti sur le distant (`pushed_sha`).
    # Nullables : les runs antérieurs n'en ont pas.
    """ALTER TABLE pipeline_runs ADD COLUMN approved_sha TEXT;
ALTER TABLE pipeline_runs ADD COLUMN pushed_sha TEXT;""",
    # 9 — ticket-604 : les tokens de création de cache de chaque appel, pour que
    # l'entrée réelle d'un rôle se lise sans sous-estimation. Les lignes
    # existantes valent 0 : la valeur n'a jamais été conservée.
    "ALTER TABLE agent_calls ADD COLUMN cache_creation_tokens INTEGER NOT NULL DEFAULT 0;",
    # 10 — ticket-665 : la date où le dépôt d'un run `interrupted` a été remis
    # d'aplomb au démarrage, pour que la reprise ne se fasse qu'une fois. Les
    # runs interrompus déjà en base sont marqués : leur dépôt a été rangé à la
    # main, et un redémarrage ne doit pas y toucher rétroactivement.
    """ALTER TABLE pipeline_runs ADD COLUMN depot_repris_at TEXT;
UPDATE pipeline_runs SET depot_repris_at = COALESCE(finished_at, started_at)
    WHERE final_status = 'interrupted';""",
    # 11 — ticket-836 : les étapes se relisent dans `agent_events` par type
    # (le détecteur d'anomalies, ADR-078) ; sans cet index, chaque lecture
    # parcourrait toute la table, tokens compris.
    "CREATE INDEX IF NOT EXISTS idx_ae_type_id ON agent_events (type, id);",
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
