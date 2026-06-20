---
id: ticket-020
title: "E2E tests — Playwright (5 flows critiques)"
type: chore
status: todo
priority: medium
agent: codeur
depends_on:
  - ticket-019
created: 2026-06-20
---

# ticket-020 — E2E tests Playwright

## Contexte

Les tests unitaires (Vitest) et d'intégration (pytest) couvrent les briques
isolées. Ce ticket ajoute des tests E2E avec Playwright pour valider les flows
critiques de bout en bout avec le vrai serveur FastAPI.

## Stack

- **Playwright** (pas de framework wrapper) — `@playwright/test`
- Tests dans `frontend/e2e/`
- CI : nouveau job `e2e` dans `.github/workflows/ci.yml` (après les jobs existants)
- Mode : serveur FastAPI mockable ou fixtures dédiées

## Flows à tester (5)

### Flow 1 — Affichage des projets
```
Given: le backend retourne une liste de projets
When: l'app se charge
Then: les projets apparaissent dans la sidebar
```

### Flow 2 — Sélection d'un projet → liste de tickets
```
Given: le projet "ide-core" existe avec des tickets
When: l'utilisateur clique sur "ide-core"
Then: la liste des tickets s'affiche dans le panel Tickets
```

### Flow 3 — Création d'un projet
```
Given: l'app est chargée
When: clic sur "+" dans le panel Projects
  → remplir name="test-e2e", description="test"
  → clic "Créer"
Then: modal fermé, "test-e2e" apparaît dans la liste, auto-sélectionné
```

### Flow 4 — Création d'un ticket
```
Given: un projet est sélectionné, panel Tickets actif
When: clic sur "+" dans le panel Tickets
  → remplir title="Ma feature", type=feat, priority=medium
  → clic "Créer"
Then: modal fermé, ticket apparaît dans la colonne todo
```

### Flow 5 — Ouverture de l'éditeur Monaco
```
Given: un ticket est visible dans la liste
When: clic sur le ticket
Then: le contenu du fichier Markdown s'affiche dans l'éditeur Monaco
  (vérifier qu'il y a du contenu, pas d'erreur)
```

## Setup

### `frontend/e2e/fixtures.ts`

```typescript
import { test as base } from '@playwright/test'
import type { Page } from '@playwright/test'

// Fixture qui démarre le backend de test ou utilise le mock server
export const test = base.extend<{ apiMock: Page }>({
  apiMock: async ({ page }, use) => {
    // Intercepter les appels API avec route()
    await page.route('/api/v1/projects', ...)
    await use(page)
  }
})
```

### Stratégie mock

Pour la CI (sans backend réel), utiliser `page.route()` de Playwright pour
intercepter les appels REST et retourner des fixtures JSON.

Pour les tests locaux avec le vrai backend, lire `BASE_URL` depuis
l'environnement.

### `playwright.config.ts`

```typescript
export default defineConfig({
  testDir: './e2e',
  use: {
    baseURL: process.env.BASE_URL ?? 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
  },
})
```

### CI — job e2e

```yaml
e2e:
  runs-on: ubuntu-latest
  needs: [frontend]   # Lance après le job frontend
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4 (node 24)
    - run: cd frontend && npm ci
    - run: cd frontend && npx playwright install --with-deps chromium
    - run: cd frontend && npm run test:e2e
    - uses: actions/upload-artifact@v4
      if: failure()
      with:
        name: playwright-report
        path: frontend/playwright-report/
```

## Critères d'acceptation

- [ ] `@playwright/test` installé dans `frontend/package.json`
- [ ] 5 tests E2E dans `frontend/e2e/`
- [ ] `npm run test:e2e` passe en local (avec mock server via `page.route()`)
- [ ] Job `e2e` dans `ci.yml` s'exécute après le job `frontend`
- [ ] Artifacts (screenshots + trace) uploadés en cas d'échec CI
- [ ] Tests indépendants (pas d'ordre requis, pas de shared state)

## Notes

- `page.route()` est préféré à un MSW ou un faux backend pour garder les tests
  rapides et sans dépendances process
- Tester uniquement les flows UI — ne pas tester la logique backend (déjà couverte par pytest)
- Screenshots `on-first-retry` pour diagnostiquer les flaky tests en CI
