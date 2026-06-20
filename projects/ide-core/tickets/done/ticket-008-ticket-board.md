---
id: ticket-008
title: "Ticket board — panneau sidebar + vue kanban dans l'IDE"
type: feat
status: done
priority: high
agent: codeur
depends_on:
  - ticket-007
created: 2026-06
---

# ticket-008 — Ticket Board (panneau IDE)

## Contexte

L'IDE est en place (ticket-007). Ce ticket implémente le panneau "Tickets"
dans la sidebar et la vue kanban optionnelle. Le ticket board n'est PAS la vue
principale — c'est un panneau dans la sidebar, comme l'explorateur de fichiers
dans VS Code. Monaco reste au centre.

## Layout cible

```
Sidebar (col 1b) — panneau Tickets actif :
┌────────────────────────────┐
│ 🎫 TICKETS — ide-core  [≡] │  ← titre + toggle vue (liste/kanban)
│ ─────────────────────────  │
│ TODO (3)                   │
│  ┌───────────────────────┐ │
│  │ ticket-007            │ │
│  │ Frontend scaffold     │ │
│  │ [high] [feat]      ▶  │ │  ← ▶ = Run Pipeline
│  └───────────────────────┘ │
│  ┌───────────────────────┐ │
│  │ ticket-008            │ │
│  │ Ticket board          │ │
│  │ [high] [feat]      ▶  │ │
│  └───────────────────────┘ │
│                             │
│ IN PROGRESS (0)            │
│ IN REVIEW (0)              │
│ DONE (6)  ▾               │  ← collapsible
│ BLOCKED (0)                │
└────────────────────────────┘
```

Vue kanban (toggle) → s'ouvre dans la zone centrale (remplace Monaco temporairement) :
```
┌──────────┬──────────────┬────────────┬──────────┐
│  TODO    │ IN PROGRESS  │  IN REVIEW │   DONE   │
│──────────│──────────────│────────────│──────────│
│ ticket-7 │              │            │ ticket-0 │
│ ticket-8 │              │            │ ticket-1 │
│ ticket-9 │              │            │ ...      │
└──────────┴──────────────┴────────────┴──────────┘
```

## Composants à créer / mettre à jour

```
src/components/
  Sidebar/
    TicketList.tsx          ← Vue liste (groupée par status, collapsible)
    TicketCard.tsx          ← Carte ticket (titre, badges, bouton Run)
  KanbanView/
    index.tsx               ← Vue kanban (panel central optionnel)
    KanbanColumn.tsx        ← Colonne par status
  TicketDetail/
    index.tsx               ← Détail ticket dans Monaco (body Markdown)
src/hooks/
  useTickets.ts             ← GET /api/v1/projects/:id/tickets + polling
  usePipeline.ts            ← POST /api/v1/orchestrator/run
```

## `useTickets` hook

```typescript
function useTickets(projectId: string | null): {
  tickets: Ticket[]
  byStatus: Record<TicketStatus, Ticket[]>
  loading: boolean
  error: string | null
  refresh: () => void
}
// Polling : 5s si un pipeline est actif, 30s sinon
```

## `usePipeline` hook

```typescript
function usePipeline(projectId: string | null): {
  run: (ticketId: string) => void
  running: Set<string>         // ticket_ids en cours
  results: Map<string, PipelineResult>
}
// POST /api/v1/orchestrator/run → déclenche aussi l'ouverture du AgentPanel (ticket-009)
```

## `TicketCard` — comportement

- **Clic simple** → ouvre `ticket.body` dans Monaco (appel `openInEditor(ticket)`)
- **Bouton ▶** → `usePipeline.run(ticket.id)` + carte passe en état `running` (spinner)
- **Badge status** coloré : todo=gray, in-progress=blue, in-review=yellow, done=green, blocked=red
- **Badge priorité** : critical=red, high=orange, medium=gray, low=slate

## Intégration Monaco

Quand on clique sur un ticket, Monaco charge son corps Markdown en mode `markdown`.
Le fichier n'est pas encore sauvegardé sur disque depuis l'éditeur (read-only en pratique).
Le `file_path` du ticket sera utilisé en ticket-010 (Tauri) pour l'édition réelle.

## Critères d'acceptation

- [ ] La sidebar "Tickets" liste les tickets groupés par status
- [ ] Les groupes DONE et CANCELLED sont collapsibles (fermés par défaut)
- [ ] Le bouton ▶ sur une carte déclenche le pipeline et passe la carte en loading
- [ ] Cliquer sur une carte charge son body Markdown dans Monaco
- [ ] Le toggle [≡] bascule entre vue liste (sidebar) et vue kanban (centre)
- [ ] Le polling refresh les tickets après la fin d'un pipeline
- [ ] `TypeScript strict` — zéro `any`

## Notes

- Utiliser `react-markdown` + `remark-gfm` pour rendre le Markdown dans Monaco (en mode preview) ou dans TicketDetail
- Le drag-and-drop (changer de colonne manuellement) est hors scope — les statuts viennent de l'API
- Le Run Pipeline → ouvre le AgentPanel (ticket-009) automatiquement
