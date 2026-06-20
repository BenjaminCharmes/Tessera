# Architecture — vibe-ide

## Vue d'ensemble

```
┌─────────────────────────────────────────┐
│            Tauri Shell (Rust)           │
│  ┌───────────────────────────────────┐  │
│  │     React UI (TypeScript)         │  │
│  │  Monaco Editor · Ticket Board     │  │
│  │  Agent Stream · Project Switcher  │  │
│  └──────────────┬────────────────────┘  │
└─────────────────┼───────────────────────┘
                  │ JSON-RPC / WebSocket
┌─────────────────▼───────────────────────┐
│       Orchestrateur (FastAPI Python)    │
│  ┌──────────┐  ┌──────────────────────┐ │
│  │ Projects │  │   Agent Runner       │ │
│  │ Tickets  │  │  (Anthropic SDK)     │ │
│  │ Memory   │  │                      │ │
│  └──────────┘  └──────────────────────┘ │
└─────────────────────────────────────────┘
                  │
         Filesystem (projets/tickets/mémoire)
```

## Flux d'un ticket

```
1. Utilisateur crée ou sélectionne un ticket (UI)
2. UI → POST /api/v1/orchestrator/run { ticket_id }
3. Orchestrateur charge le contexte projet
4. Orchestrateur → AgentRunner.run(role=CODEUR, ticket, context)
5. AgentRunner → Anthropic API (streaming)
6. Tokens streamés → WS /orchestrator/stream → UI
7. AgentResult reçu → Orchestrateur décide
8. Si FEAT/FIX → AgentRunner.run(role=REVIEWER, code, ticket)
9. APPROVED → ticket déplacé vers done/
10. CHANGES_REQUESTED → retour à l'étape 4 (max 3 tours)
```

## Structure des fichiers de tickets

```
projects/{project_id}/tickets/
  todo/
    ticket-000-backend-structure.md
    ticket-001-models.md
  in-progress/
    ticket-002-project-loader.md   ← déplacé ici quand commencé
  done/
    ticket-xxx-completed.md
```

Chaque ticket est un Markdown avec frontmatter YAML :
```yaml
---
id: ticket-000
title: Description courte
type: feat | fix | chore | design | docs
status: todo | in-progress | in-review | done | blocked
priority: critical | high | medium | low
agent: codeur | reviewer | architect | ...
depends_on: []
created: 2025-06-01
---
Corps du ticket en Markdown...
```

## Communication inter-agents

Les agents ne se parlent pas directement.
Ils communiquent via l'Orchestrateur qui :
1. Passe le résultat de l'agent A comme contexte supplémentaire à l'agent B
2. Décide du routing selon le résultat
3. Maintient l'historique des échanges dans le ticket

## Mémoire des projets

```
projects/{project_id}/memory/
  decisions.md      ← ADRs, décisions d'architecture
  stack.md          ← versions, commandes, ports
  entities.md       ← glossaire du domaine (optionnel)
  pipeline-log.md   ← historique des pipelines (auto-généré)
```

## Ajout d'un nouveau type d'agent

1. Créer `agents/prompts/{role}.md` avec le system prompt
2. Ajouter l'entrée dans `projects/{project_id}/agents.json`
3. Ajouter le role dans l'enum `AgentRole` (`models/agent.py`)
4. Si pipeline custom nécessaire : modifier `Orchestrator.run_pipeline()`

Pas besoin de modifier le reste du code.
