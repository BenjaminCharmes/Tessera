# Tessera

> IDE multi-projets avec orchestration d'agents IA — se construit lui-même.

[![CI](https://github.com/BenjaminCharmes/tessera/actions/workflows/ci.yml/badge.svg)](https://github.com/BenjaminCharmes/tessera/actions/workflows/ci.yml)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![Tests](https://img.shields.io/badge/tests-260%20frontend%20%2B%20566%20backend-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-74%25%20backend%20%7C%2080%25%20frontend-green)
![TypeScript](https://img.shields.io/badge/TypeScript-strict-blue)
![Tauri](https://img.shields.io/badge/Tauri-v2-orange)

---

## Qu'est-ce que c'est ?

Tessera est un orchestrateur d'agents IA qui gère des projets logiciels sous forme de tickets Markdown.
Il implémente un pipeline **codeur → testeur → sécurité → reviewer → validateur → doc-updater** alimenté par Claude,
avec un support GitHub intégré (Issues, PRs, clone).

Les agents **écrivent réellement les fichiers** et chaque run de pipeline s'exécute sur sa **propre branche git**,
qu'il termine par un commit — ce qui est relu, audité et validé, c'est le diff réel, pas la prose de l'agent.

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

### Phase 6 — Pipeline enrichi + qualité ✅

| Feature | Status |
|---------|--------|
| Agent doc-updater — mise à jour auto de la documentation post-pipeline | ✅ |
| Agent testeur — exécution des tests dans le pipeline (pytest/npm/cargo) | ✅ |
| Agent validateur — vérification critère par critère des ACs du ticket | ✅ |
| Agent sécurité — audit OWASP automatique avant le reviewer | ✅ |
| Coverage tooling — pytest-cov backend + v8 frontend (74% backend) | ✅ |

### Phase 7 — Exécution réelle ✅

| Feature | Status |
|---------|--------|
| Provider Claude Agent SDK — fonctionne sur l'abonnement, sans crédits API | ✅ |
| Provider Anthropic API en fallback (Docker, CI, sessions non interactives) | ✅ |
| Les agents écrivent réellement les fichiers (outils fichier du SDK) | ✅ |
| Une branche git par run de pipeline, forkée d'une ref de base stable | ✅ |
| Le pipeline relit le **diff git réel**, plus la prose du codeur | ✅ |
| Commit automatique à chaque run (typé si approuvé, `chore:` sinon) | ✅ |
| Un ticket approuvé devient la base du ticket suivant (mode autonome) | ✅ |
| **Chat conversationnel** avec outils fichier, streaming et coût visible | ✅ |

### Phase 8 — Couverture et outillage ✅

| Feature | Status |
|---------|--------|
| Couverture des routers portée à 93,5 % | ✅ |
| Quota d'abonnement réel remonté par le fournisseur (ADR-020) | ✅ |
| Lancement d'un pipeline depuis le chat | ✅ |
| Outillage Windows (`doctor`, `scripts/tessera.ps1`) | ✅ |

### Phase 9 — Le projet appartient à l'utilisateur ✅

| Feature | Status |
|---------|--------|
| Lier un projet à un dépôt, ou en initialiser un | ✅ |
| Artefacts Tessera versionnés ou locaux, **par projet** (ADR-021, ADR-023) | ✅ |
| Le défaut échoue fermé : un projet importé garde ses artefacts chez lui | ✅ |
| Retirer un projet de l'IDE sans perdre ses fichiers | ✅ |
| Suivi par ticket, push et ouverture de PR — **jamais de merge** (ADR-022) | ✅ |
| Un projet doit être la racine de son propre dépôt (ADR-024) | ✅ |

### Phase 10 — Cockpit, dialogue et intégrité ✅

| Feature | Status |
|---------|--------|
| **Pivot cockpit** : l'IDE pilote la flotte, VSCode édite (ticket-065) | ✅ |
| Arbre de fichiers et éditeur en lecture seule | ✅ |
| **Dialogue pendant un run** : l'agent demande, l'utilisateur intervient | ✅ |
| Reprise sur hypothèse énoncée si personne ne répond (ADR-025) | ✅ |
| Cohérence visuelle : cinq familles de couleurs à rôle (ADR-026) | ✅ |
| **Les agents ne touchent pas à l'historique git** (ADR-027) | ✅ |
| Un run qui échoue à committer ne peut pas se dire approuvé | ✅ |

---

## Documentation

| Document | Pour qui |
|----------|----------|
| [Guide utilisateur](docs/guide-utilisateur.md) | Tu **utilises** Tessera sur tes projets |
| [Architecture](docs/architecture.md) | Tu veux comprendre comment il est construit |
| [Stratégie de tickets](docs/ticket-strategy.md) | Tu découpes un backlog |
| [ADR](projects/ide-core/memory/decisions.md) | Les décisions d'architecture et leur pourquoi |

---

## Démarrage rapide

### Lancement via Docker (recommandé)

Seul prérequis : [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```bash
git clone https://github.com/BenjaminCharmes/tessera.git
cd tessera

# 1. Crée le fichier .env avec ta clef API
cp .env.example .env
# Édite .env et renseigne ANTHROPIC_API_KEY=sk-ant-...

# 2. Lance tout en une commande
docker compose up --build
```

- **Frontend** : http://localhost:5173
- **Backend API** : http://localhost:8000/docs

Les données persistentes (workspace + SQLite) survivent à `docker compose down` via le volume nommé `tessera-data` et le bind-mount `./projects/`.

**Protection optionnelle par token** : ajoute `STATIC_TOKEN=mon-secret` dans `.env` pour exiger `Authorization: Bearer mon-secret` sur tous les appels API (utile si l'IDE est exposé sur un serveur distant).

```bash
# Arrêter
docker compose down

# Arrêter et supprimer les volumes (RESET total)
docker compose down -v
```

---

### Lancement local (développement)

### Prérequis

- Python 3.11+ et [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Node.js 24 LTS (`nvm install --lts`)
- Rust stable (`curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`)
- **Soit** un abonnement Claude avec une session Claude Code authentifiée (mode par
  défaut, `LLM_PROVIDER=agent_sdk` — aucune clef API nécessaire),
  **soit** une clef API Anthropic ([console.anthropic.com](https://console.anthropic.com/))
  si tu passes en `LLM_PROVIDER=anthropic_api`

### Installation

#### Linux / macOS

```bash
git clone https://github.com/BenjaminCharmes/tessera.git
cd tessera

make setup      # .env + dépendances
make doctor     # vérifie les prérequis AVANT de lancer
make run        # backend + frontend
make stop       # arrête tout
```

#### Windows

`make` n'est pas installé par défaut sous Windows, et `make run` repose sur
`trap`/`wait`, sémantiques POSIX. Utilise le script équivalent :

```powershell
git clone https://github.com/BenjaminCharmes/tessera.git
cd tessera

.\scriptsibe.ps1 setup
.\scriptsibe.ps1 doctor
.\scriptsibe.ps1 run
.\scriptsibe.ps1 stop
```

> **Lance `doctor` en premier.** Il vérifie Python, `.env`, le workspace, les
> prompts des agents, l'authentification du provider, les symlinks et les
> ports. Les deux pannes qui ont coûté une session de débogage — une
> `ANTHROPIC_API_KEY` parasite et un chemin de prompts qui ne résolvait jamais
> — étaient l'une et l'autre détectables par ce contrôle.

> **Le piège du worker orphelin** : ne lance pas uvicorn avec `--reload` si tu
> enchaînes des modifications. Tuer le parent laisse l'enfant vivant, qui garde
> le port 8000 et sert le code de son dernier rechargement — d'où des `500`
> inexplicables et un port qu'aucun `Stop-Process` ne libère.
> `tessera.ps1 stop` et `make stop` le ciblent par sa ligne de commande.

Le backend démarre sur **http://localhost:8000** et le frontend sur **http://localhost:5173**.
La documentation interactive (Swagger) est disponible sur **http://localhost:8000/docs**.

> **Développement avancé** : `make dev` lance uniquement le backend, `make dev-frontend` lance uniquement le frontend.

### Lancement desktop (app Tauri)

#### Mode dev

```bash
make dev          # terminal 1 — backend FastAPI sur :8000
make tauri-dev    # terminal 2 — app desktop avec hot-reload frontend
```

#### Build de production (app packagée)

```bash
make tauri-build
```

Le bundle produit se trouve dans `frontend/src-tauri/target/release/bundle/` :
- **macOS** : `macos/Tessera.app` (double-clic pour lancer)

Le bundle **démarre automatiquement le backend** au lancement de l'app — aucun terminal supplémentaire requis.  
Prérequis : `uv` doit être dans le `PATH` de l'environnement qui exécute l'app.  
Le backend se coupe automatiquement à la fermeture de la fenêtre.

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
Tessera/
├── .env.example              ← Template de configuration (copier en .env)
├── Makefile                  ← Commandes de lancement (make dev, make test...)
├── CLAUDE.md                 ← Constitution du projet pour les agents IA
│
├── backend/                  ← Orchestrateur Python/FastAPI
│   ├── pyproject.toml
│   ├── src/tessera/
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
│   │   │   ├── orchestrator.py     ← Pipeline enrichi (testeur→securite→reviewer→validateur→doc-updater)
│   │   │   ├── ticket_service.py   ← CRUD tickets sur filesystem
│   │   │   ├── project_loader.py   ← Chargement CLAUDE.md + agents.json
│   │   │   ├── project_creator.py  ← Création projet + auto-agents
│   │   │   ├── project_importer.py ← Import local (symlink/copy)
│   │   │   ├── project_analyzer.py ← Génération CLAUDE.md depuis code
│   │   │   ├── test_runner.py      ← Exécution tests (pytest/npm/cargo), timeout 120s
│   │   │   ├── security_auditor.py ← Audit OWASP (BLOCK si CRITICAL/HIGH)
│   │   │   ├── validator.py        ← Validation critères d'acceptation
│   │   │   ├── doc_updater.py      ← Mise à jour docs post-approbation
│   │   │   ├── planner.py          ← Description NL → batch de tickets
│   │   │   ├── git_clone.py        ← Clone repo GitHub
│   │   │   ├── github_service.py   ← Client httpx pour GitHub API
│   │   │   └── sync_map.py         ← Correspondances ticket ↔ issue
│   │   └── agents/
│   │       └── github_sync.py      ← Sync bidirectionnelle tickets ↔ issues
│   └── tests/                ← 429 tests (pytest + respx) — couverture 74%
│
├── agents/
│   └── prompts/              ← System prompts de chaque agent (Markdown)
│       ├── codeur.md
│       ├── reviewer.md
│       ├── orchestrateur.md
│       ├── architect.md
│       ├── project-creator.md
│       ├── project-analyzer.md
│       ├── planificateur.md
│       ├── doc-updater.md
│       ├── testeur.md
│       ├── validateur.md
│       └── securite.md
│
├── projects/
│   └── ide-core/             ← Projet bootstrap (l'IDE se construit lui-même)
│       ├── CLAUDE.md
│       ├── agents.json
│       ├── tickets/
│       │   └── done/         ← 38 tickets terminés ✅ (Phases 1–6 complètes)
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
| `LLM_PROVIDER` | | `agent_sdk` | `agent_sdk` (abonnement Claude) ou `anthropic_api` (crédits API) |
| `ANTHROPIC_API_KEY` | si `anthropic_api` | — | Clef API Anthropic — inutile en mode `agent_sdk` |
| `LLM_MAX_TURNS` | | `30` | Plafond d'allers-retours outil pour un agent |
| `LLM_MAX_BUDGET_USD` | | `1.0` | Plafond de dépense d'un seul appel agent |
| `RUN_MAX_BUDGET_USD` | | `5.0` | Plafond cumulé d'un run autonome (`0` = aucun) |
| `CHAT_MAX_CONVERSATION_USD` | | `2.0` | Plafond cumulé d'une conversation du chat |
| `IDE_WORKSPACE_DIR` | | `~/tessera-workspace` | Dossier des projets |
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
make test-coverage # Rapport de couverture backend + frontend
make lint          # Type-check mypy
make clean         # Supprime les caches
```

Tests frontend :

```bash
cd frontend
npm run test          # Vitest unit tests (260 tests)
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
        ├─ git checkout -b ticket-XXX-slug   (forkée de la ref de base)
        │
        ├─ Codeur (Claude) ──streaming──▶ WS /orchestrator/stream
        │       ↓ écrit réellement les fichiers
        ├─ git diff  →  c'est CE diff que relisent les agents suivants
        │
        ├─ Testeur            → exécute la suite de tests du projet
        ├─ Sécurité (OWASP)   → BLOCK si CRITICAL/HIGH  →  ticket → blocked/
        ├─ Reviewer (Claude)
        │       ↓ CHANGES_REQUESTED  →  retour Codeur (max 3 tours)
        │       ↓ APPROVED
        ├─ Validateur         → vérifie les critères d'acceptation un par un
        ├─ Doc-updater        → met à jour README / docs / CLAUDE.md
        │
        ├─ git commit
        │       ↓ approuvé      →  "<type>: ticket-XXX — <titre>"  + ref de base avancée
        │       ↓ non approuvé  →  "chore: ticket-XXX — unapproved work (<raison>)"
        │
        └─ PipelineResult { approved, rounds, final_status, branch, commit_sha }
```

> Quel que soit le verdict, le travail du codeur est commité sur la branche du
> ticket : rien n'est perdu, et l'arbre de travail reste propre pour le ticket
> suivant. Seul un ticket **approuvé** fait avancer la ref de base, de sorte
> qu'un plan de tickets séquentiels s'empile correctement sans jamais hériter
> du travail rejeté d'un ticket précédent.

---

## Philosophie

- **Self-hosting** : l'IDE se construit lui-même via `projects/ide-core/`
- **Tickets = fichiers Markdown** : lisibles sans l'IDE, versionnables avec git
- **Agents découplés** : chaque agent a un system prompt, l'orchestrateur gère le routing
- **Pas de framework agent** : on contrôle le protocole (pas LangChain/CrewAI)
- **Immutabilité** : les données ne sont jamais mutées en place, toujours copiées
