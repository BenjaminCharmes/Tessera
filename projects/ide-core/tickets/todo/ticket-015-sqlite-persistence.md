---
id: ticket-015
title: "SQLite — persistence de l'historique des pipelines"
type: feat
status: todo
priority: medium
agent: codeur
depends_on:
  - ticket-013
created: 2026-06-20
---

# ticket-015 — SQLite persistence

## Contexte

Décidé depuis ADR-003 : SQLite est la couche de cache/historique au-dessus des
fichiers Markdown (qui restent la source de vérité). Actuellement, toute l'histoire
des runs d'agents est perdue à chaque redémarrage du serveur.

Ce ticket ajoute `aiosqlite` et persiste l'historique des pipelines.

## Tâches

### 1. Dépendance

```toml
# backend/pyproject.toml
[project]
dependencies = [
  ...
  "aiosqlite>=0.20.0",
]
```

### 2. `backend/src/vibe_ide/services/database.py`

```python
import aiosqlite
from pathlib import Path

DB_PATH = Path("vibe_ide.db")

CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id          TEXT PRIMARY KEY,
    project_id  TEXT NOT NULL,
    ticket_id   TEXT NOT NULL,
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    rounds      INTEGER,
    approved    INTEGER,
    final_status TEXT
);

CREATE TABLE IF NOT EXISTS agent_events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id     TEXT NOT NULL REFERENCES pipeline_runs(id),
    type       TEXT NOT NULL,
    agent      TEXT,
    data_json  TEXT,
    timestamp  TEXT NOT NULL
);
"""

async def init_db() -> None: ...
async def save_run(run: PipelineRun) -> None: ...
async def save_event(run_id: str, event: OrchestratorEvent) -> None: ...
async def list_runs(project_id: str, limit: int = 50) -> list[dict]: ...
```

### 3. Intégration dans `main.py`

```python
from contextlib import asynccontextmanager
from vibe_ide.services.database import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(lifespan=lifespan)
```

### 4. Intégration dans `Orchestrator`

À la fin de `run_pipeline()`, appeler `save_run()` et `save_event()` pour chaque
`OrchestratorEvent` émis pendant le pipeline.

### 5. Endpoint `GET /api/v1/projects/{project_id}/runs`

```python
@router.get("/{project_id}/runs")
async def list_project_runs(
    project_id: str,
    limit: int = 20
) -> list[PipelineRunSummary]:
    ...
```

Réponse :
```json
[
  {
    "id": "uuid",
    "ticket_id": "ticket-011",
    "started_at": "2026-06-20T14:30:00Z",
    "finished_at": "2026-06-20T14:32:15Z",
    "rounds": 2,
    "approved": true,
    "final_status": "done"
  }
]
```

### 6. Tests

- `backend/tests/test_database.py` :
  - `test_init_db_creates_tables`
  - `test_save_run_persists`
  - `test_list_runs_returns_ordered`
  - Utiliser une DB temporaire en mémoire (`":memory:"`) pour les tests

## Critères d'acceptation

- [ ] `aiosqlite` ajouté à `pyproject.toml` et `uv.lock`
- [ ] `init_db()` crée les tables au démarrage (idempotent)
- [ ] Chaque pipeline complété est enregistré dans `pipeline_runs`
- [ ] Les events WS sont enregistrés dans `agent_events`
- [ ] `GET /api/v1/projects/{id}/runs` retourne les 20 derniers runs
- [ ] `pytest` passe avec les nouveaux tests (DB en mémoire)
- [ ] `vibe_ide.db` est dans `.gitignore` (déjà couvert par `*.db`)

## Notes

- `DB_PATH` par défaut à la racine du projet (configurable via `.env`)
- Pas d'ORM (sqlalchemy serait overkill) — requêtes SQL manuelles avec aiosqlite
- Les fichiers Markdown restent la source de vérité (ADR-003)
- SQLite en WAL mode pour éviter les locks en écriture concurrente
