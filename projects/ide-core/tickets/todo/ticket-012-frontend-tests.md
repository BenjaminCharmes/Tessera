---
id: ticket-012
title: "Tests frontend — Vitest + React Testing Library"
type: chore
status: todo
priority: high
agent: codeur
depends_on:
  - ticket-011
created: 2026-06-20
---

# ticket-012 — Tests frontend

## Contexte

Le frontend (tickets 007-010) a 0% de couverture de tests. Le backend a sa suite
pytest. Ce ticket ajoute Vitest + React Testing Library pour atteindre 80% de
couverture sur les hooks et utilitaires.

## Pourquoi Vitest et pas Jest

Vitest partage la config Vite (transforms, aliases, env). Pas de config babel
séparée. Les tests s'exécutent en ESM natif, identique au bundle de prod.

## Tâches

### 1. Installation

```bash
cd frontend
npm install -D vitest @vitest/coverage-v8 jsdom \
  @testing-library/react @testing-library/user-event \
  @testing-library/jest-dom
```

### 2. `vite.config.ts` — ajouter la section test

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    coverage: {
      provider: 'v8',
      include: ['src/lib/**', 'src/hooks/**'],
      thresholds: { lines: 80, branches: 70 },
    },
  },
})
```

### 3. `src/test/setup.ts`

```typescript
import '@testing-library/jest-dom'
```

### 4. Scripts `package.json`

```json
"test": "vitest run",
"test:watch": "vitest",
"test:coverage": "vitest run --coverage"
```

### 5. Tests à écrire

#### `src/lib/ws.test.ts`
```typescript
describe('wsUrl', () => {
  it('builds ws:// URL from http location', ...)
  it('builds wss:// URL from https location', ...)
})
```

#### `src/lib/api.test.ts`
```typescript
// Mock fetch, tester les cas ok + erreur pour projects.list, tickets.list
describe('api.projects.list', () => {
  it('returns parsed projects on 200', ...)
  it('throws ApiError on non-200', ...)
})
```

#### `src/hooks/useActiveProject.test.ts`
```typescript
describe('useActiveProject', () => {
  it('setProject resets ticket to null', ...)
  it('setTicket works independently', ...)
})
```

#### `src/hooks/useOrchestratorStream.test.ts`
```typescript
// Mock WebSocket global
describe('useOrchestratorStream', () => {
  it('starts idle', ...)
  it('transitions to connecting on connect()', ...)
  it('accumulates tokens from agent_token events', ...)
  it('sets lastResult on pipeline_done', ...)
})
```

#### `src/components/AgentPanel/VerdictBanner.test.tsx`
```typescript
describe('VerdictBanner', () => {
  it('shows APPROVED banner', ...)
  it('shows CHANGES_REQUESTED banner', ...)
  it('shows nothing when no verdict keyword', ...)
})
```

#### `src/components/Sidebar/TicketCard.test.tsx`
```typescript
describe('TicketCard', () => {
  it('renders ticket title', ...)
  it('shows run button for todo tickets', ...)
  it('shows animate-pulse when running', ...)
  it('calls onRunPipeline with ticket id on click', ...)
})
```

### 6. Mock WebSocket global

```typescript
// src/test/mocks/websocket.ts
class MockWebSocket {
  static instances: MockWebSocket[] = []
  readyState = WebSocket.CONNECTING
  // ... implémentation minimale pour les tests
}
globalThis.WebSocket = MockWebSocket as unknown as typeof WebSocket
```

## Critères d'acceptation

- [ ] `npm run test` passe sans erreur (toutes les suites vertes)
- [ ] `npm run test:coverage` montre ≥80% de lignes sur `src/lib/` et `src/hooks/`
- [ ] Tests VerdictBanner couvrent les 3 cas (approved / changes requested / neutre)
- [ ] Tests TicketCard couvrent le bouton ▶ et l'état running
- [ ] Tests useOrchestratorStream couvrent les transitions d'état et l'accumulation de tokens
- [ ] Pas de test qui dépend d'un backend tournant (tout mocké)

## Notes

- Utiliser `renderHook` de RTL pour les hooks
- Mock `fetch` avec `vi.stubGlobal('fetch', vi.fn())`
- Ne pas tester les détails d'implémentation CSS (classes Tailwind)
- L'objectif est de tester le comportement, pas le rendu exact
