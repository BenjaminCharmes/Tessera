---
id: ticket-012
title: "Tests frontend — Vitest + React Testing Library"
type: chore
status: done
priority: high
agent: codeur
depends_on:
  - ticket-011
created: 2026-06-20
completed: 2026-06-20
---

# ticket-012 — Tests frontend ✅

## Ce qui a été fait

### Stack

- `vitest@4.1.9` + `@vitest/coverage-v8`
- `@testing-library/react@16` + `@testing-library/user-event` + `@testing-library/jest-dom`
- `jsdom` comme environnement de test

### Configuration

**`vite.config.ts`** — section `test` ajoutée :
- `environment: "jsdom"`, `globals: true` (requis par jest-dom pour étendre `expect`)
- `setupFiles: ["./src/test/setup.ts"]`
- Coverage V8, seuil 80% lignes / 70% branches sur `src/lib/**` et `src/hooks/**`

**`tsconfig.app.json`** — ajout de `"vitest/globals"` dans les types.

**Correction Rolldown** : `globals: true` requis car `@testing-library/jest-dom` étend
`expect` global — sans ça, `ReferenceError: expect is not defined` au setup.

### Tests écrits — 36 tests, 6 fichiers

| Fichier | Tests |
|---------|-------|
| `src/lib/ws.test.ts` | wsUrl: proto ws/wss, path préservé |
| `src/lib/api.test.ts` | projects.list, tickets.list, orchestrator.run — 200 + erreurs |
| `src/hooks/useActiveProject.test.ts` | état initial, setProject réinitialise ticket |
| `src/hooks/useOrchestratorStream.test.ts` | idle→connecting→running, tokens, pipeline_done, error, clear, null projectId |
| `src/components/AgentPanel/VerdictBanner.test.tsx` | APPROVED, CHANGES_REQUESTED, priorité CHANGES > APPROVED |
| `src/components/Sidebar/TicketCard.test.tsx` | rendu, onSelect, onRun, stopPropagation, animate-pulse, disabled, done/cancelled sans bouton |

### Mock WebSocket (`src/test/mockWebSocket.ts`)

Classe `MockWebSocket` avec `triggerOpen/triggerMessage/triggerClose` pour simuler les
events WS en tests sans vraie connexion réseau.

## Résultats

```
Tests  36 passed (36)
Files  6 passed (6)
Duration  1.39s
```
