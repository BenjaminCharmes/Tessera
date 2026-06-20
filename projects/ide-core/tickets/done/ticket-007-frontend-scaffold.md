---
id: ticket-007
title: "Frontend scaffold — Layout IDE + Monaco Editor embarqué"
type: feat
status: done
priority: high
agent: codeur
depends_on: []
created: 2026-06
---

# ticket-007 — Frontend scaffold (IDE-first)

## Contexte

Ce ticket pose les fondations visuelles de vibe-ide : **un vrai IDE**, pas une web app.
L'éditeur Monaco (le moteur de VS Code) est la pièce centrale. Le ticket board et
le panneau agent sont des panneaux dans l'IDE, pas des vues principales.

## Layout cible

```
┌──────────────────────────────────────────────────────────────────┐
│  vibe-ide                                              [−][□][✕] │  ← titlebar
├──────┬─────────────────────────────────┬────────────────────────-┤
│      │  ticket-007-frontend-scaffold.md│                          │
│  Nav │  ──────────────────────────── │   Agent Panel            │
│      │                                 │   (ticket-009)           │
│  📁  │         Monaco Editor           │                          │
│  ide │         (code / markdown)       │   Idle — en attente      │
│  core│                                 │   d'un pipeline          │
│      │                                 │                          │
│  🎫  │                                 │                          │
│  KBd │                                 │                          │
│      ├─────────────────────────────────┤                          │
│      │  Pipeline Log                   │                          │
└──────┴─────────────────────────────────┴──────────────────────────┘
  col1        col2 (flex)                      col3
```

- **Col 1 (sidebar)** : navigation projets + tickets (icônes toggleables)
- **Col 2 (centre)** : Monaco Editor — pièce centrale
- **Col 3 (droite)** : Agent Stream Panel — actif pendant un pipeline
- **Bas** : Pipeline Log (bottom panel, collapsible)

## Arborescence cible

```
frontend/
  package.json
  vite.config.ts
  tsconfig.json
  tailwind.config.ts
  postcss.config.js
  index.html
  src/
    main.tsx
    App.tsx                   ← Layout 3 colonnes + bottom panel (CSS Grid)
    types/
      api.ts                  ← Types TS miroir des modèles Pydantic
    lib/
      api.ts                  ← Fetch client (/api/v1)
      ws.ts                   ← Utilitaire WebSocket réutilisable
    components/
      Sidebar/
        index.tsx             ← Shell sidebar (icônes + panel actif)
        ProjectNav.tsx        ← Liste des projets (accordéon)
        TicketList.tsx        ← Liste tickets du projet actif (placeholder ticket-008)
      Editor/
        index.tsx             ← Monaco Editor wrapper
        useMonaco.ts          ← Hook d'initialisation Monaco
      AgentPanel/
        index.tsx             ← Panneau droit (placeholder ticket-009)
      BottomPanel/
        index.tsx             ← Pipeline log (placeholder)
    hooks/
      useProjects.ts          ← GET /api/v1/projects
      useActiveProject.ts     ← State du projet sélectionné
```

## Types API (`src/types/api.ts`)

Reflet exact des modèles Pydantic — **zéro `any`** :

```typescript
export type TicketStatus = "todo" | "in-progress" | "in-review" | "done" | "blocked" | "cancelled"
export type TicketType = "feat" | "fix" | "chore" | "design" | "docs"
export type TicketPriority = "critical" | "high" | "medium" | "low"
export type AgentRole = "orchestrateur" | "codeur" | "reviewer" | "architect" | "project-creator" | "github-sync"
export type EventType = "agent_started" | "agent_token" | "agent_done" | "ticket_status_changed" | "pipeline_done" | "error"

export interface Ticket {
  id: string
  title: string
  type: TicketType
  status: TicketStatus
  priority: TicketPriority
  agent: string
  depends_on: string[]
  created: string
  github_issue_url: string | null
  body: string
  project_id: string
  file_path: string
}

export interface Project {
  id: string
  name: string
  description: string
  active_agents: string[]
  stack: string | null
  raw_claude_md: string
}

export interface OrchestratorEvent {
  type: EventType
  agent: AgentRole | null
  ticket_id: string
  data: Record<string, unknown>
  timestamp: string
}

export interface PipelineResult {
  ticket_id: string
  final_status: TicketStatus
  rounds: number
  approved: boolean
}
```

## Monaco Editor (`src/components/Editor/`)

```typescript
// useMonaco.ts
import * as monaco from "@monaco-editor/react"

export function useMonaco(containerRef: RefObject<HTMLDivElement>) {
  // Initialise Monaco avec :
  // - Thème : "vs-dark"
  // - Langages actifs : markdown, python, typescript, json
  // - Options : minimap désactivée, wordWrap: "on", fontSize: 14
  // - readOnly: false (édition locale, pas encore persistée)
}
```

Quand un ticket est sélectionné dans la sidebar → son `body` Markdown s'ouvre dans Monaco.

## `vite.config.ts`

```typescript
server: {
  proxy: {
    "/api": { target: "http://localhost:8000", changeOrigin: true },
  }
}
```

Les WebSocket utilisent le proxy Vite également via `ws: true` pour :
- `/api/v1/orchestrator/stream`
- `/api/v1/agents/stream`

## `App.tsx` — Layout CSS Grid

```tsx
// Grille 3 colonnes + bottom panel
<div className="grid h-screen grid-cols-[48px_280px_1fr_320px] grid-rows-[1fr_200px]">
  <IconBar />                    {/* col 1a — icônes */}
  <Sidebar />                    {/* col 1b — panel actif */}
  <Editor />                     {/* col 2 — Monaco */}
  <AgentPanel />                 {/* col 3 — agents (span 2 rows) */}
  <BottomPanel />                {/* row 2, cols 1-2 */}
</div>
```

## Critères d'acceptation

- [ ] `npm run dev` lance sur http://localhost:5173 sans erreur
- [ ] `npm run build` produit un bundle TypeScript valide (strict: true, zéro any)
- [ ] Monaco Editor s'affiche au centre avec le thème dark
- [ ] La sidebar liste les projets disponibles (appel API réel)
- [ ] Sélectionner un projet met à jour l'état global
- [ ] Cliquer sur un ticket dans la sidebar ouvre son `body` dans Monaco
- [ ] Le layout 3 colonnes est responsive (col3 collapsible sur petit écran)
- [ ] Tailwind + PostCSS fonctionnels

## Notes

- Package Monaco : `@monaco-editor/react` (wrapper React officiel)
- Le thème `vs-dark` est le thème par défaut — un thème custom vibe-ide peut venir plus tard
- Pas de persistance de l'édition Monaco pour ce ticket (read-only en pratique, édition locale non sauvegardée)
- `npm run tauri dev` sera ajouté par ticket-010 — pour l'instant, web seulement
