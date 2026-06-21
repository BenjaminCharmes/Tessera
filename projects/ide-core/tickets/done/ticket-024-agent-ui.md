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
created: 2026-06-21
---

# ticket-024 — UI gestion des agents

## Contexte

Exposer la gestion des agents dans la sidebar avec un panneau dédié et une
modale conversationnelle pour créer de nouveaux agents.

## Composants à créer

### `frontend/src/components/Sidebar/AgentList.tsx`

Liste tous les agents retournés par `GET /agents/registry` :
- Badge "built-in" (bleu) vs "custom" (vert)
- Bouton de suppression pour les custom uniquement
- Preview du system prompt au survol

### `frontend/src/components/Sidebar/AgentCreatorModal.tsx`

Calqué sur `CreateProjectModal.tsx` — interface conversationnelle :
- Textarea pour décrire l'agent voulu
- Appelle `POST /agents/create-agent` avec `{ conversation: [...] }`
- Si `created: false` → affiche la question de clarification, l'utilisateur répond
- Si `created: true` → ferme la modale + toast "Agent `{role}` créé"

### Étendre `frontend/src/components/Sidebar/index.tsx`

```typescript
export type SidebarPanel = "projects" | "tickets" | "history" | "agents";
```

Ajouter l'icône ⚙ dans `IconBar` → ouvre le panneau `agents`.

## Types et API client

`frontend/src/types/api.ts` :
```typescript
export interface AgentInfo {
  role: string;
  description: string | null;
  is_builtin: boolean;
  prompt_preview: string;
}
```

`frontend/src/lib/api.ts` :
```typescript
agents: {
  list: (): Promise<AgentInfo[]> => request("/agents/registry"),
  remove: (role: string): Promise<void> => request(`/agents/registry/${role}`, { method: "DELETE" }),
  createConversational: (conversation: ConversationMessage[]) =>
    request("/agents/create-agent", { method: "POST", body: { conversation } }),
},
```

## Hook

`frontend/src/hooks/useAgents.ts` — même pattern que `useRuns.ts`.

## Critères de done

- [ ] `AgentList.tsx` avec badge built-in/custom + suppression custom
- [ ] `AgentCreatorModal.tsx` conversationnelle (multi-tour)
- [ ] Panneau sidebar `"agents"` avec icône dans `IconBar`
- [ ] `useAgents` hook
- [ ] Types dans `api.ts`, appels dans `lib/api.ts`
- [ ] Tests Vitest/RTL : `AgentList` (renders, delete), `AgentCreatorModal` (submit)
- [ ] `npm run build` passe
