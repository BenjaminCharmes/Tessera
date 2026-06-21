---
id: ticket-024
title: "UI gestion des agents (sidebar + modale conversationnelle)"
type: feat
status: done
priority: high
agent: codeur
depends_on:
  - ticket-022
  - ticket-023
estimated_days: 1.5
created: 2026-06-21
---

# ticket-024 — UI gestion des agents

## Objectif

Exposer la gestion des agents dans la sidebar avec un panneau dédié et une modale conversationnelle pour créer de nouveaux agents. L'utilisateur peut voir, supprimer et créer des agents sans quitter l'IDE.

## Contexte

Avec tickets 021-023, le backend est complet. Ce ticket crée l'interface frontend : panneau agents dans la sidebar, liste avec badges built-in/custom, et modale conversationnelle multi-tour qui appelle `/agents/create-agent`.

## Solution implémentée

- **`frontend/src/hooks/useAgents.ts`** — hook global (pattern `useRuns`, sans projectId)
- **`frontend/src/components/Sidebar/AgentList.tsx`** — liste avec badges, suppression au survol
- **`frontend/src/components/Sidebar/AgentCreatorModal.tsx`** — modale conversationnelle multi-tour
- **`frontend/src/components/Sidebar/index.tsx`** — `SidebarPanel` étendu à `"agents"`, icône ⚙
- **`frontend/src/types/api.ts`** — `AgentInfo`, `ConversationMessage`, `CreateAgentResponse`
- **`frontend/src/lib/api.ts`** — helper `del()` + namespace `agents.*`

## Critères d'acceptation

- [x] La sidebar affiche un panneau agents avec l'icône ⚙
- [x] Chaque agent affiche un badge "built-in" (bleu) ou "custom" (vert)
- [x] Seuls les agents custom ont un bouton de suppression (au survol)
- [x] La modale conversationnelle s'adapte selon la réponse du backend (`created: true/false`)
- [x] Un toast "Agent `{role}` créé" apparaît après création réussie

## Dépendances

- **ticket-022** — `GET/DELETE /agents/registry` pour liste et suppression.
- **ticket-023** — `POST /agents/create-agent` pour la modale conversationnelle.

## Estimation

**1.5j** (réalisé)
