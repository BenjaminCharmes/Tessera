# vibe-ide

> IDE multi-projets avec orchestration d'agents IA — se construit lui-même.

[![CI](https://github.com/BenjaminCharmes/vibe_ide/actions/workflows/ci.yml/badge.svg)](https://github.com/BenjaminCharmes/vibe_ide/actions/workflows/ci.yml)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![Tests](https://img.shields.io/badge/tests-184%20frontend%20%2B%20365%20backend-brightgreen)
![TypeScript](https://img.shields.io/badge/TypeScript-strict-blue)
![Tauri](https://img.shields.io/badge/Tauri-v2-orange)

---

## Qu'est-ce que c'est ?

vibe-ide est un orchestrateur d'agents IA qui gère des projets logiciels sous forme de tickets Markdown.
Il implémente un pipeline **codeur → reviewer** alimenté par Claude (Anthropic), avec un support GitHub intégré (Issues, PRs, clone).

Le projet suit le pattern **self-hosting** : `projects/ide-core/` contient les tickets qui ont servi à construire l'IDE lui-même.

---

## Fonctionnalités

### Phase 1–4 — Fondations + IDE fonctionnel ✅

| Feature | Status |
|---------|--------|
| Gestion de projets multi-projets | ✅ |
| Tickets Markdown avec frontmatter YAML | ✅ |
| Agent Codeur (Claude, streaming) | ✅ |
| Agent Reviewer (pipeline codeur→reviewer, max 3 tours) | ✅ |
| Orchestrateur multi-agents avec events WebSocket | ✅ |
| Mode autonome (traite les tickets en séquence) | ✅ |
| Agent GitHub Sync (Issues → tickets Markdown) | ✅ |
| Agent Project Creator (nouveau projet via conversation) | ✅ |
| Frontend React (ticket board, agent stream, Monaco) | ✅ |
| Shell desktop Tauri v2 (fenêtre native macOS) | ✅ |
| CI GitHub Actions (backend + frontend + e2e + tauri) | ✅ |
| Monaco branché sur le filesystem réel | ✅ |
| UI création de projet / ticket (modales + sidebar) | ✅ |
| SQLite persistence (historique des pipelines) | ✅ |
| Live ticket board (WS events → mise à jour temps réel) | ✅ |
| Panneau historique des pipelines (sidebar) | ✅ |
| UX polish (ErrorBoundary, toasts, skeletons, empty states) | ✅ |
| E2E tests Playwright (5 flows critiques) | ✅ |

### Phase 5 — Agents dynamiques + intégration GitHub ✅

| Feature | Status |
|---------|--------|
| Registre d'agents dynamiques (AgentRegistryService) | ✅ |
| API CRUD agents (GET/POST/DELETE /api/v1/agents/registry) | ✅ |
| Agent conversationnel agent-creator (nouveau agent via chat) | ✅ |
| UI gestion des agents (sidebar panel ⚙ + modale conversationnelle) | ✅ |
| Import projet local existant (modes symlink & copy) | ✅ |
| Agent project-analyzer (génération CLAUDE.md depuis le code) | ✅ |
| UI import de projet (3 étapes : source → analyse → validation) | ✅ |
| Agent planificateur (description NL → batch de tickets) | ✅ |
| UI « Planifier une évolution » + persistance batch | ✅ |
| Clone de repo GitHub dans le workspace | ✅ |
| Synchronisation bidirectionnelle tickets ↔ GitHub Issues | ✅ |
| Intégration GitHub Pull Requests (création + statut CI) | ✅ |
| Création automatique des agents manquants à la création de projet | ✅ |

---

## Démarrage rapide

### Prérequis

- Python 3.11+ et [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Node.js 24 LTS (`nvm install --lts`)
- Rust stable (`curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`)
- Une clef API Anthropic ([console.anthropic.com](https://console.anthropic.com/))

### Installation

```bash
git clone https://github.com/BenjaminCharmes/vibe_ide.git
cd vibe_ide

# 1. Initialise l'environnement (.env + dépendances)
make setup

# 2. Ouvre .env et colle ta clef API
#    ANTHROPIC_API_KEY=sk-ant-...

# 3. Lance le serveur
make dev
```

Le serveur démarre sur **http://localhost:8000**.
La documentation interactive (Swagger) est disponible sur **http://localhost:8000/docs**.

### Tester l'API manuellement

```bash
# Créer un nouveau projet via l'agent Project Creator
curl -X POST http://localhost:8000/api/v1/agents/create-project \
  -H "Content-Type: application/json" \
  -d '{"conversation": [{"role": "user", "content": "Crée un projet Todo App en Python"}]}'

# Importer un projet local existant
curl -X POST http://localhost:8000/api/v1/projects/import \
  -H "Content-Type: application/json" \
  -d '{"source_path": "/path/to/project", "mode": "symlink"}'

# Cloner un repo GitHub
curl -X POST http://localhost:8000/api/v1/projects/clone \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/owner/repo"}'

# Lister les projets
curl http://localhost:8000/api/v1/projects

# Lancer le pipeline codeur→reviewer sur un ticket
curl -X POST http://localhost:8000/api/v1/orchestrator/run \
  -H "Content-Type: application/json" \
  -d '{"project_id": "ide-core", "ticket_id": "ticket-007"}'

# Streaming WebSocket (wscat requis : npm i -g wscat)
wscat -c ws://localhost:8000/api/v1/orchestrator/stream/ide-core
# → envoyer : {"ticket_id": "ticket-007"}
```

---

## Structure du monorepo

```
vibe-ide/
├── .env.example              ← Template de configuration (copier en .env)
├── Makefile                  ← Commandes de lancement (make dev, make test...)
├── CLAUDE.md                 ← Constitution du projet pour les agents IA
│
├── backend/                  ← Orchestrateur Python/FastAPI
│   ├── pyproject.toml
│   ├── src/vibe_ide/
│   │   ├── main.py           ← Point d'entrée FastAPI
│   │   ├── config.py         ← Settings (pydantic-settings, lit .env)
│   │   ├── models/           ← Pydantic models (Ticket, Agent, Project)
│   │   ├── routers/          ← Endpoints HTTP + WebSocket
│   │   │   ├── projects.py   ← CRUD projets + clone + analyze + plan
│   │   │   ├── tickets.py    ← CRUD tickets + batch + PR
│   │   │   ├── agents.py     ← run/stream + create-project/agent
│   │   │   ├── agent_admin.py← CRUD registre agents dynamiques
│   │   │   └── orchestrator.py ← pipeline run/autonomous + WS stream
│   │   ├── services/
│   │   │   ├── agent_runner.py     ← Appels Anthropic (streaming + complet)
│   │   │   ├── agent_registry.py   ← Registre agents (lecture/écriture prompts)
│   │   │   ├── agent_creator.py    ← Création agent via conversation
│   │   │   ├── orchestrator.py     ← Pipeline codeur→reviewer
│   │   │   ├── ticket_service.py   ← CRUD tickets sur filesystem
│   │   │   ├── project_loader.py   ← Chargement CLAUDE.md + agents.json
│   │   │   ├── project_creator.py  ← Création projet + auto-agents
│   │   │   ├── project_importer.py ← Import local (symlink/copy)
│   │   │   ├── project_analyzer.py ← Génération CLAUDE.md depuis code
│   │   │   ├── planner.py          ← Description NL → batch de tickets
│   │   │   ├── git_clone.py        ← Clone repo GitHub
│   │   │   ├── github_service.py   ← Client httpx pour GitHub API
│   │   │   └── sync_map.py         ← Correspondances ticket ↔ issue
│   │   └── agents/
│   │       └── github_sync.py      ← Sync bidirectionnelle tickets ↔ issues
│   └── tests/                ← 365 tests (pytest + respx)
│
├── agents/
│   └── prompts/              ← System prompts de chaque agent (Markdown)
│       ├── codeur.md
│       ├── reviewer.md
│       ├── orchestrateur.md
│       ├── architect.md
│       ├── project-creator.md
│       ├── project-analyzer.md
│       └── planificateur.md
│
├── projects/
│   └── ide-core/             ← Projet bootstrap (l'IDE se construit lui-même)
│       ├── CLAUDE.md
│       ├── agents.json
│       ├── tickets/
│       │   ├── done/         ← 34 tickets terminés ✅ (Phases 1–5 complètes)
│       │   └── todo/         ← 4 tickets phase 6 en attente
│       └── memory/
│           └── decisions.md  ← ADRs documentés
│
├── docs/
│   ├── architecture.md       ← Vue d'ensemble technique
│   └── ticket-strategy.md    ← Stratégie hybride GitHub ↔ Markdown
│
└── frontend/                 ← React + TypeScript + Tailwind + Vite
```

---

## Référence API

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/api/v1/projects` | Liste tous les projets |
| `POST` | `/api/v1/projects` | Crée un projet → `ProjectCreationResult` |
| `POST` | `/api/v1/projects/import` | Importe un projet local (symlink/copy) |
| `POST` | `/api/v1/projects/clone` | Clone un repo GitHub |
| `GET` | `/api/v1/projects/:id` | Détail d'un projet |
| `GET` | `/api/v1/projects/:id/runs` | Historique des pipelines (SQLite) |
| `POST` | `/api/v1/projects/:id/analyze` | Génère CLAUDE.md depuis le code |
| `POST` | `/api/v1/projects/:id/plan` | Description NL → batch de tickets |
| `POST` | `/api/v1/projects/:id/github/sync` | Sync tickets ↔ GitHub Issues |
| `GET` | `/api/v1/projects/:id/tickets` | Liste les tickets |
| `POST` | `/api/v1/projects/:id/tickets` | Crée un ticket |
| `POST` | `/api/v1/projects/:id/tickets/batch` | Crée plusieurs tickets d'un coup |
| `PATCH` | `/api/v1/projects/:id/tickets/:tid/status` | Change le statut |
| `POST` | `/api/v1/projects/:id/tickets/:tid/create-pr` | Ouvre une PR GitHub |
| `GET` | `/api/v1/projects/:id/tickets/:tid/pr-status` | Statut CI de la PR |
| `GET` | `/api/v1/agents/registry` | Liste les agents (builtins + custom) |
| `GET` | `/api/v1/agents/registry/:role` | Prompt d'un agent |
| `POST` | `/api/v1/agents/registry` | Crée / met à jour un agent |
| `DELETE` | `/api/v1/agents/registry/:role` | Supprime un agent custom |
| `POST` | `/api/v1/agents/create-project` | Crée un projet via conversation |
| `POST` | `/api/v1/agents/create-agent` | Crée un agent via conversation |
| `POST` | `/api/v1/agents/run` | Exécute un agent sur un ticket |
| `WS` | `/api/v1/agents/stream` | Stream de tokens d'un agent |
| `POST` | `/api/v1/orchestrator/run` | Lance le pipeline codeur→reviewer |
| `POST` | `/api/v1/orchestrator/run-autonomous` | Mode autonome (N tickets) |
| `WS` | `/api/v1/orchestrator/stream/:project_id` | Stream des OrchestratorEvents |

---

## Configuration

Toutes les variables sont dans `.env` (copie de `.env.example`) :

| Variable | Requis | Default | Description |
|----------|--------|---------|-------------|
| `ANTHROPIC_API_KEY` | ✅ | — | Clef API Anthropic |
| `IDE_WORKSPACE_DIR` | | `~/vibe-ide-workspace` | Dossier des projets |
| `IDE_PROMPTS_DIR` | | `agents/prompts/` | Dossier des system prompts |
| `IDE_LOG_LEVEL` | | `INFO` | Niveau de log |
| `GITHUB_TOKEN` | | `""` | Token GitHub (sync issues, clone, PRs) |
| `GITHUB_REPO` | | `""` | Repo cible `owner/repo` |

---

## Commandes de développement

```bash
make setup         # Initialisation complète (première fois)
make dev           # Lance FastAPI sur http://localhost:8000
make dev-frontend  # Lance Vite sur http://localhost:5173
make tauri-dev     # Lance l'app desktop Tauri (nécessite make dev)
make tauri-build   # Build production (.app distributable)
make test          # Tests Python (pytest)
make test-fast     # Tests Python rapides
make lint          # Type-check mypy
make clean         # Supprime les caches
```

Tests frontend :

```bash
cd frontend
npm run test          # Vitest unit tests (184 tests)
npm run test:coverage # Rapport de couverture
npm run test:e2e      # Playwright E2E (5 flows, nécessite npm run dev)
```

---

## Architecture

```
┌─────────────────────────────────────┐
│      ✅ Tauri v2 Shell (Rust)       │
│  ┌─────────────────────────────┐    │
│  │  ✅ React UI (TypeScript)   │    │
│  │  Monaco · Ticket Board      │    │
│  │  Agent Stream · Sidebar     │    │
│  └──────────────┬──────────────┘    │
└─────────────────┼───────────────────┘
               │ HTTP / WebSocket
┌──────────────▼──────────────────────┐
│     Orchestrateur (FastAPI)         │
│                                     │
│  ┌─────────────┐  ┌───────────────┐ │
│  │  Routers    │  │   Services    │ │
│  │  projects   │  │  AgentRunner  │ │
│  │  tickets    │  │  Orchestrator │ │
│  │  agents     │  │  AgentRegistry│ │
│  │  agent_adm  │  │  Planner      │ │
│  │  orchestr.  │  │  GitClone     │ │
│  └─────────────┘  └───────┬───────┘ │
└──────────────────────────-┼─────────┘
                            │ Anthropic SDK
                    ┌───────▼───────┐
                    │  Claude API   │
                    │ (Sonnet 4.6 / │
                    │  Haiku 4.5)   │
                    └───────────────┘
                            │
               Filesystem (tickets/memory/)
               GitHub API (issues/PRs/clone)
```

### Flux d'un ticket

```
POST /orchestrator/run { project_id, ticket_id }
        │
        ├─ Codeur (Claude) ──streaming──▶ WS /orchestrator/stream
        │       ↓ code produit
        ├─ Reviewer (Claude)
        │       ↓ APPROVED  →  ticket → done/ + PR optionnelle
        │       ↓ CHANGES_REQUESTED  →  retour Codeur (max 3 tours)
        │       ↓ 3 tours sans approbation  →  ticket → blocked/
        └─ PipelineResult { approved, rounds, final_status }
```

---

## Philosophie

- **Self-hosting** : l'IDE se construit lui-même via `projects/ide-core/`
- **Tickets = fichiers Markdown** : lisibles sans l'IDE, versionnables avec git
- **Agents découplés** : chaque agent a un system prompt, l'orchestrateur gère le routing
- **Pas de framework agent** : on contrôle le protocole (pas LangChain/CrewAI)
- **Immutabilité** : les données ne sont jamais mutées en place, toujours copiées
