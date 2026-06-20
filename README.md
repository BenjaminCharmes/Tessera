# vibe-ide

> IDE multi-projets avec orchestration d'agents IA — se construit lui-même.

[![CI](https://github.com/BenjaminCharmes/vibe-ide/actions/workflows/ci.yml/badge.svg)](https://github.com/BenjaminCharmes/vibe-ide/actions/workflows/ci.yml)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green)
![Tests](https://img.shields.io/badge/tests-140%20passing-brightgreen)

---

## Qu'est-ce que c'est ?

vibe-ide est un orchestrateur d'agents IA qui gère des projets logiciels sous forme de tickets Markdown.
Il implémente un pipeline **codeur → reviewer** alimenté par Claude (Anthropic), avec un support GitHub Issues intégré.

Le projet suit le pattern **self-hosting** : `projects/ide-core/` contient les tickets qui ont servi à construire l'IDE lui-même.

---

## Fonctionnalités (v0 — backend complet)

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
| Frontend React (ticket board, agent stream) | 🔜 ticket-007 |
| Shell desktop Tauri | 🔜 futur |

---

## Démarrage rapide

### Prérequis

- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Une clef API Anthropic ([console.anthropic.com](https://console.anthropic.com/))

### Installation

```bash
git clone https://github.com/BenjaminCharmes/vibe-ide.git
cd vibe-ide

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

# Lister les projets
curl http://localhost:8000/api/v1/projects

# Lister les tickets d'un projet
curl http://localhost:8000/api/v1/projects/ide-core/tickets

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
│   │   │   ├── projects.py   ← GET/POST /api/v1/projects
│   │   │   ├── tickets.py    ← CRUD /api/v1/projects/:id/tickets
│   │   │   ├── agents.py     ← POST /api/v1/agents/run + /stream WS
│   │   │   └── orchestrator.py ← POST /run, /run-autonomous + /stream WS
│   │   ├── services/
│   │   │   ├── agent_runner.py    ← Appels Anthropic (streaming + complet)
│   │   │   ├── orchestrator.py    ← Pipeline codeur→reviewer, pick_next_ticket
│   │   │   ├── ticket_service.py  ← CRUD tickets sur filesystem
│   │   │   ├── project_loader.py  ← Chargement CLAUDE.md
│   │   │   ├── project_creator.py ← Création projet via agent
│   │   │   └── github_service.py  ← Client httpx pour GitHub API
│   │   └── agents/
│   │       └── github_sync.py     ← Agent de sync GitHub Issues → tickets
│   └── tests/                ← 140 tests (pytest + respx)
│
├── agents/
│   └── prompts/              ← System prompts de chaque agent (Markdown)
│       ├── codeur.md
│       ├── reviewer.md
│       ├── orchestrateur.md
│       ├── architect.md
│       └── project-creator.md
│
├── projects/
│   └── ide-core/             ← Projet bootstrap (l'IDE se construit lui-même)
│       ├── CLAUDE.md
│       ├── agents.json
│       ├── tickets/
│       │   └── done/         ← Les 6 premiers tickets sont terminés ✅
│       └── memory/
│           └── decisions.md  ← 11 ADRs documentés
│
├── docs/
│   ├── architecture.md       ← Vue d'ensemble technique
│   └── ticket-strategy.md    ← Stratégie hybride GitHub ↔ Markdown
│
└── frontend/                 ← (ticket-007) React + TypeScript + Tailwind
```

---

## Référence API

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/api/v1/projects` | Liste tous les projets |
| `POST` | `/api/v1/projects` | Crée un projet (structure filesystem) |
| `GET` | `/api/v1/projects/:id` | Détail d'un projet |
| `GET` | `/api/v1/projects/:id/tickets` | Liste les tickets (filtre par status) |
| `GET` | `/api/v1/projects/:id/tickets/:tid` | Détail d'un ticket |
| `PATCH` | `/api/v1/projects/:id/tickets/:tid/status` | Change le status |
| `POST` | `/api/v1/agents/run` | Exécute un agent sur un ticket |
| `WS` | `/api/v1/agents/stream` | Stream de tokens d'un agent |
| `POST` | `/api/v1/agents/create-project` | Crée un projet via conversation |
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
| `GITHUB_TOKEN` | | `""` | Token GitHub (agent github-sync) |
| `GITHUB_REPO` | | `""` | Repo cible `owner/repo` |

---

## Commandes de développement

```bash
make setup        # Initialisation complète (première fois)
make dev          # Lance le serveur en mode reload
make test         # Suite de tests complète (140 tests)
make test-fast    # Tests rapides (sortie minimaliste)
make lint         # Type-check mypy
make clean        # Supprime les caches
```

---

## Architecture

```
┌─────────────────────────────────────┐
│     Frontend (ticket-007 — 🔜)      │
│   React 18 · TypeScript · Tailwind  │
│   Monaco Editor · Ticket Board      │
└──────────────┬──────────────────────┘
               │ HTTP / WebSocket
┌──────────────▼──────────────────────┐
│     Orchestrateur (FastAPI)         │
│                                     │
│  ┌─────────────┐  ┌───────────────┐ │
│  │  Routers    │  │   Services    │ │
│  │  projects   │  │  AgentRunner  │ │
│  │  tickets    │  │  Orchestrator │ │
│  │  agents     │  │  TicketSvc    │ │
│  │  orchestr.  │  │  GithubSync   │ │
│  └─────────────┘  └───────┬───────┘ │
└──────────────────────────-┼─────────┘
                            │ Anthropic SDK
                    ┌───────▼───────┐
                    │  Claude API   │
                    │ (Sonnet 4.6)  │
                    └───────────────┘
                            │
               Filesystem (tickets/memory/)
```

### Flux d'un ticket

```
POST /orchestrator/run { project_id, ticket_id }
        │
        ├─ Codeur (Claude) ──streaming──▶ WS /orchestrator/stream
        │       ↓ code produit
        ├─ Reviewer (Claude)
        │       ↓ APPROVED  →  ticket → done/
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
