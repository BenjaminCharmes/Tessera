---
id: ticket-015
title: "SQLite — persistence de l'historique des pipelines"
type: feat
status: done
priority: medium
agent: codeur
depends_on:
  - ticket-013
created: 2026-06-20
completed: 2026-06-20
---

# ticket-015 — SQLite persistence ✅

## Ce qui a été fait

### `backend/src/vibe_ide/services/database.py` (nouveau)

Fonctions async pures, chacune ouvre/ferme sa propre connexion :
- `init_db(db_path)` — crée les tables (idempotent, WAL mode activé)
- `create_run(db_path, project_id, ticket_id)` → UUID du run
- `finish_run(db_path, run_id, rounds, approved, final_status)`
- `save_event(db_path, run_id, type, agent, data, timestamp)`
- `list_runs(db_path, project_id, limit=20)` → liste ordonnée DESC

Modèle Pydantic `PipelineRunSummary` défini ici (utilisé comme response model).

Tables SQLite :
```sql
pipeline_runs  (id, project_id, ticket_id, started_at, finished_at, rounds, approved, final_status)
agent_events   (id AUTOINCREMENT, run_id, type, agent, data_json, ts)
```

### `backend/src/vibe_ide/config.py`
- `ide_db_path: Path = Path("vibe_ide.db")` — configurable via `IDE_DB_PATH`

### `backend/src/vibe_ide/main.py`
- Lifespan FastAPI : `init_db(settings.ide_db_path)` au démarrage

### `backend/src/vibe_ide/routers/orchestrator.py`
- `POST /run` : crée run avant pipeline, wraps callback pour sauver events, `finish_run` après
- `WS /stream` : même logique pour le mode single-ticket (le mode autonome stream sans DB pour la v0)

### `backend/src/vibe_ide/routers/projects.py`
- `GET /{project_id}/runs?limit=20` → `list[PipelineRunSummary]`

### `backend/tests/test_database.py` — 7 nouveaux tests
Isolation via `tmp_path` pytest (pas de mocks, vraie DB SQLite) :
- `test_init_db_creates_tables`
- `test_init_db_is_idempotent`
- `test_save_run_persists`
- `test_list_runs_returns_ordered`
- `test_list_runs_filters_by_project`
- `test_list_runs_respects_limit`
- `test_save_event_persists`

## Résultats

```
147 tests backend passent (+ 7 nouveaux)
vibe_ide.db dans .gitignore (couvert par *.db)
```
