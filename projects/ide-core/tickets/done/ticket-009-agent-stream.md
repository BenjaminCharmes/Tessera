---
id: ticket-009
title: "Agent stream panel — WebSocket temps réel dans l'IDE"
type: feat
status: done
priority: high
agent: codeur
depends_on:
  - ticket-008
created: 2026-06
---

# ticket-009 — Agent Stream Panel

## Contexte

Le pipeline se déclenche depuis le ticket board (ticket-008). Ce ticket implémente
le panneau droit de l'IDE qui affiche les tokens de Claude en temps réel, les transitions
codeur↔reviewer, et le verdict final — comme un terminal de build, mais pour les agents.

## Layout cible (panneau col3 de l'IDE)

```
┌─────────────────────────────────────┐
│ ⚡ AGENTS — ticket-007     [−][✕]  │  ← header + minimize/close
│─────────────────────────────────────│
│  🔵 Tour 1 / 3                      │  ← RoundBadge
│                                     │
│  ┌─ 🤖 CODEUR ──────────────────┐  │
│  │ ●●●  (streaming en cours)    │  │  ← spinner actif
│  │                               │  │
│  │  def create_project(name):    │  │
│  │      return Project(          │  │  ← tokens en temps réel
│  │          id=slugify(name),    │  │
│  │          ...                  │  │
│  └───────────────────────────────┘  │
│                                     │
│  ┌─ 🔍 REVIEWER ─────────────────┐  │
│  │  APPROVED ✅                  │  │  ← VerdictBanner (vert)
│  │  Code propre, tests présents. │  │
│  └───────────────────────────────┘  │
│                                     │
│  ✅ Pipeline terminé — 1 tour (18s) │  ← PipelineSummary
│─────────────────────────────────────│
│  [▶ Relancer]  [📋 Copier le code] │  ← actions
└─────────────────────────────────────┘
```

## Composants à créer

```
src/components/AgentPanel/
  index.tsx               ← Shell du panneau (état idle / running / done)
  RoundBadge.tsx          ← "Tour N / max" avec barre de progression
  AgentBlock.tsx          ← Bloc pour un agent (codeur ou reviewer)
  TokenStream.tsx         ← Affichage des tokens caractère par caractère
  VerdictBanner.tsx       ← APPROVED (vert) ou CHANGES_REQUESTED (orange)
  PipelineSummary.tsx     ← Récapitulatif final (status, rounds, durée)

src/hooks/
  useOrchestratorStream.ts  ← WebSocket /orchestrator/stream/{project_id}
```

## `useOrchestratorStream` hook

```typescript
interface StreamState {
  status: "idle" | "connecting" | "running" | "done" | "error"
  events: OrchestratorEvent[]
  currentAgent: AgentRole | null
  currentRound: number
  currentTokens: string           // tokens du tour codeur en cours (reset à chaque tour)
  lastResult: PipelineResult | null
  errorMessage: string | null
}

function useOrchestratorStream(projectId: string | null): StreamState & {
  connect: (ticketId: string) => void
  disconnect: () => void
  clear: () => void
}
```

### Comportement du hook

```
connect(ticketId)
  → ouvre WebSocket ws://localhost:8000/api/v1/orchestrator/stream/{projectId}
  → envoie { "ticket_id": ticketId }
  → écoute les OrchestratorEvent :

  "ticket_status_changed"  → met à jour le status du ticket dans useTickets
  "agent_started"          → currentAgent = event.agent, currentRound = event.data.round
  "agent_token"            → currentTokens += event.data.token   (codeur uniquement)
  "agent_done"             → si reviewer → parse verdict → VerdictBanner
  "pipeline_done"          → lastResult = ..., status = "done", ferme WS
  "error"                  → status = "error", affiche errorMessage
```

### Reconnexion automatique

Si la WS se ferme de façon inattendue en cours de pipeline :
- Réessayer 3 fois avec backoff (1s, 2s, 4s)
- Après 3 échecs → status = "error"

## Intégration avec le ticket board (ticket-008)

Dans `usePipeline.run(ticketId)` :
1. Appeler `connect(ticketId)` du stream hook
2. Le panneau AgentPanel passe de `idle` à `connecting` → `running`
3. À `pipeline_done` : refresh des tickets via `useTickets.refresh()`
4. Le AgentPanel reste visible jusqu'à ce que l'utilisateur le ferme

## Bottom Panel — Pipeline Log

Le bottom panel (placeholder dans ticket-007) affiche ici le log textuel compact :
```
[14:32:01] ticket-007 — in-progress
[14:32:02] Codeur démarré (tour 1)
[14:32:18] Codeur terminé (16s)
[14:32:19] Reviewer démarré
[14:32:24] APPROVED — ticket-007 → done
```

C'est le contenu de `projects/{id}/memory/pipeline-log.md` affiché en streaming.

## Critères d'acceptation

- [ ] Déclencher Run depuis le ticket board ouvre le AgentPanel et affiche les tokens
- [ ] Les tokens du codeur s'affichent en temps réel (pas de batch)
- [ ] Le RoundBadge "Tour N/max" est visible et se met à jour
- [ ] VerdictBanner vert pour APPROVED, orange pour CHANGES_REQUESTED
- [ ] À `pipeline_done` : PipelineSummary affiché + ticket board refreshé
- [ ] La WS se reconnecte automatiquement si interrompue (3 tentatives)
- [ ] Le bouton [✕] ferme le panneau proprement (disconnect WS)
- [ ] Le bottom panel affiche les transitions en log textuel
- [ ] `TypeScript strict` — zéro `any`

## Notes

- Pas de `any` dans les types des events — utiliser le type union `OrchestratorEvent`
- Le mode autonome (`run-autonomous`) peut être ajouté comme un bouton "Run All" dans le header du panneau — hors scope pour ce ticket
- Utiliser `useRef` pour l'auto-scroll du TokenStream vers le bas
