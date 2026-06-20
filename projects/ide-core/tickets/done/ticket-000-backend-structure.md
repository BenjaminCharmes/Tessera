---
id: ticket-000
title: Structure de base du backend
type: chore
status: done
priority: critical
agent: codeur
depends_on: []
created: 2025-06
---

# ticket-000 — Structure de base du backend

## Contexte

Point de départ absolu. Rien n'existe encore dans `backend/`.
Ce ticket pose le squelette sur lequel tout le reste sera construit.

## Tâche

Créer la structure complète du backend Python avec :

### Arborescence cible

```
backend/
  pyproject.toml         ← config uv + dépendances
  .python-version        ← "3.11"
  src/
    vibe_ide/
      __init__.py
      main.py            ← entrypoint FastAPI
      config.py          ← settings via pydantic-settings
      models/
        __init__.py
        ticket.py        ← modèle Ticket (Pydantic)
        project.py       ← modèle Project (Pydantic)
        agent.py         ← modèle Agent (Pydantic)
      routers/
        __init__.py
        projects.py      ← GET /projects, POST /projects
        tickets.py       ← GET /tickets, PATCH /tickets/{id}
        agents.py        ← POST /agents/run
      services/
        __init__.py
        project_loader.py  ← lit CLAUDE.md, structure dossiers
        ticket_service.py  ← CRUD tickets (fichiers Markdown)
      utils/
        __init__.py
        logger.py        ← logger structuré JSON
  tests/
    __init__.py
    test_ticket.py
    test_project_loader.py
```

### Contenu de pyproject.toml

```toml
[project]
name = "vibe-ide"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.111.0",
    "uvicorn[standard]>=0.30.0",
    "anthropic>=0.28.0",
    "pydantic>=2.7.0",
    "pydantic-settings>=2.3.0",
    "aiosqlite>=0.20.0",
    "python-frontmatter>=1.1.0",
    "websockets>=12.0",
    "httpx>=0.27.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.27.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

### config.py

Utiliser `pydantic-settings` pour lire depuis les variables d'environnement :
- `ANTHROPIC_API_KEY` (requis)
- `IDE_WORKSPACE_DIR` (défaut: `~/vibe-ide-workspace`)
- `IDE_LOG_LEVEL` (défaut: `INFO`)

### main.py

- App FastAPI avec titre "vibe-ide"
- Inclure tous les routers avec prefix `/api/v1`
- Endpoint `GET /health` retournant `{"status": "ok", "version": "0.1.0"}`
- CORS configuré pour localhost:5173 (frontend Vite)

## Critères d'acceptation

- [ ] `uv sync` fonctionne sans erreur
- [ ] `uv run fastapi dev src/vibe_ide/main.py` démarre sur le port 8765
- [ ] `GET /health` retourne 200
- [ ] `uv run pytest` passe (même si peu de tests pour l'instant)
- [ ] Tous les fichiers sont typés (mypy compatible)

## Notes pour le codeur

- Ne pas implémenter la logique des routers pour l'instant — juste les stubs avec `return []`
- La vraie logique vient dans ticket-001 et ticket-002
- Garder `main.py` sous 50 lignes
