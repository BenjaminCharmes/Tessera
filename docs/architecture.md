# Architecture — vibe-ide

## Vue d'ensemble

```
┌─────────────────────────────────────────┐
│       ✅ Tauri v2 Shell (Rust)          │   ← ticket-010
│  ┌───────────────────────────────────┐  │
│  │   ✅ React UI (TypeScript)        │  │   ← tickets 007-009
│  │  Monaco Editor · Ticket Board     │  │
│  │  Agent Stream · Project Switcher  │  │
│  └──────────────┬────────────────────┘  │
└─────────────────┼───────────────────────┘
                  │ HTTP + WebSocket
┌─────────────────▼───────────────────────┐
│       Orchestrateur (FastAPI Python)    │   ← ✅ implémenté
│                                         │
│  Routers                Services        │
│  ├─ /projects      ├─ ProjectLoader     │
│  ├─ /tickets       ├─ TicketService     │
│  ├─ /agents        ├─ AgentRunner       │
│  └─ /orchestrator  ├─ Orchestrator      │
│                    ├─ ProjectCreator    │
│                    ├─ GitHubService     │
│                    └─ GithubSyncAgent   │
│                           │             │
│                    Anthropic SDK        │
└─────────────────────────────────────────┘
                  │
         Filesystem (tickets Markdown + mémoire)
```

## Endpoints implémentés

### Projets
| Méthode | Route | Description |
|---------|-------|-------------|
| `GET` | `/api/v1/projects` | Liste tous les projets (dossiers avec CLAUDE.md) |
| `POST` | `/api/v1/projects` | Crée la structure filesystem d'un projet |
| `GET` | `/api/v1/projects/{id}` | Charge le projet et son CLAUDE.md |

### Tickets
| Méthode | Route | Description |
|---------|-------|-------------|
| `GET` | `/api/v1/projects/{id}/tickets` | Liste les tickets (optionnel: `?status=todo`) |
| `POST` | `/api/v1/projects/{id}/tickets` | Crée un ticket (génère le fichier Markdown) |
| `GET` | `/api/v1/projects/{id}/tickets/{tid}` | Détail d'un ticket |
| `PATCH` | `/api/v1/projects/{id}/tickets/{tid}/status` | Déplace le ticket dans le bon dossier |

### Agents
| Méthode | Route | Description |
|---------|-------|-------------|
| `POST` | `/api/v1/agents/run` | Exécute un agent sur un ticket (sans streaming) |
| `WS` | `/api/v1/agents/stream` | Exécute un agent avec streaming de tokens |
| `POST` | `/api/v1/agents/create-project` | Crée un projet via conversation multi-tours |

### Orchestrateur
| Méthode | Route | Description |
|---------|-------|-------------|
| `POST` | `/api/v1/orchestrator/run` | Lance le pipeline codeur→reviewer |
| `POST` | `/api/v1/orchestrator/run-autonomous` | Mode autonome (N tickets en séquence) |
| `WS` | `/api/v1/orchestrator/stream/{project_id}` | Stream des OrchestratorEvents en temps réel |

## Flux d'un ticket

```
1. Ticket en todo/ → POST /orchestrator/run { project_id, ticket_id }
2. Orchestrateur: ticket → in-progress/
3. Codeur (Claude) → produit le code
   └─ tokens streamés via WS → UI en temps réel
4. Ticket → in-review/
5. Reviewer (Claude) → lit le code produit
   ├─ "APPROVED" → ticket → done/ ; pipeline terminé
   └─ "CHANGES_REQUESTED: {raison}" → retour au Codeur avec feedback
        (max 3 tours ; sinon ticket → blocked/)
6. PipelineResult { ticket_id, final_status, rounds, approved }
7. OrchestratorEvent.PIPELINE_DONE envoyé via WebSocket
```

## Structure des fichiers de tickets

```
projects/{project_id}/tickets/
  todo/
    ticket-007-frontend-scaffold.md
  in-progress/
    ticket-008-ticket-board.md        ← déplacé quand commencé
  in-review/
    ticket-XXX.md                     ← le reviewer évalue
  done/
    ticket-000-backend-structure.md
    ticket-001-models-ticket-service.md
    ticket-002-project-loader.md
    ticket-003-agent-loop.md
    ticket-004-project-creator.md
    ticket-005-orchestrator.md
    ticket-006-agent-github-sync.md
```

Chaque ticket = fichier Markdown avec frontmatter YAML :
```yaml
---
id: ticket-007
title: Frontend scaffold — Vite + React + Tailwind
type: feat
status: todo
priority: high
agent: codeur
depends_on: []
created: 2026-06
github_issue_url: https://github.com/...  # optionnel
---
Corps du ticket en Markdown...
```

## OrchestratorEvents (WebSocket)

Les clients WebSocket reçoivent des `OrchestratorEvent` au format JSON :

```json
{
  "type": "agent_started | agent_token | agent_done | ticket_status_changed | pipeline_done | error",
  "agent": "codeur | reviewer | null",
  "ticket_id": "ticket-007",
  "data": { "round": 1, "token": "def foo", "status": "in-progress", "approved": true },
  "timestamp": "2026-06-20T14:30:00Z"
}
```

## Agents disponibles

| Rôle | Modèle | Usage |
|------|--------|-------|
| `codeur` | claude-sonnet-4-6 | Implémente les tickets feat/fix |
| `reviewer` | claude-sonnet-4-6 | Valide le code produit |
| `orchestrateur` | claude-sonnet-4-6 | Décompose les tickets complexes |
| `architect` | claude-sonnet-4-6 | Analyse architecturale |
| `project-creator` | claude-sonnet-4-6 | Crée de nouveaux projets |
| `github-sync` | — (pas de LLM) | Synchronise GitHub Issues → tickets |

## Communication inter-agents

Les agents ne se parlent pas directement.
L'Orchestrateur :
1. Passe le résultat du Codeur comme contexte au Reviewer
2. Injecte les feedbacks reviewer précédents dans le contexte du Codeur (tour suivant)
3. Décide du routing selon le verdict (`APPROVED` / `CHANGES_REQUESTED`)
4. Logue chaque transition dans `projects/{id}/memory/pipeline-log.md`

## Mémoire des projets

```
projects/{project_id}/memory/
  decisions.md      ← ADRs, décisions d'architecture
  stack.md          ← versions, commandes, ports
  pipeline-log.md   ← historique des pipelines (auto-généré par l'Orchestrateur)
```

## Ajout d'un nouveau type d'agent

1. Créer `agents/prompts/{role}.md` avec le system prompt
2. Ajouter l'entrée dans `projects/{project_id}/agents.json`
3. Ajouter le role dans l'enum `AgentRole` (`models/agent.py`)
4. Si pipeline custom : modifier `Orchestrator.run_pipeline()`

Pas besoin de modifier le reste du code.
