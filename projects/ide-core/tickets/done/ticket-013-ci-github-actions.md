---
id: ticket-013
title: "CI — GitHub Actions (backend + frontend + tauri)"
type: chore
status: done
priority: high
agent: codeur
depends_on:
  - ticket-012
created: 2026-06-20
completed: 2026-06-20
---

# ticket-013 — CI GitHub Actions ✅

## Ce qui a été fait

### `.github/workflows/ci.yml` — 3 jobs parallèles

| Job | Runner | Steps |
|-----|--------|-------|
| Backend (pytest) | ubuntu-latest | uv sync → pytest -m "not integration" → mypy |
| Frontend (tsc + vitest) | ubuntu-latest | npm ci → tsc --noEmit → npm run test |
| Tauri (cargo check) | macos-latest | rust-toolchain → rust-cache → cargo check |

### Fix intégration tests

`test_run_real_api` était marqué `@pytest.mark.integration` mais la condition
de skip vérifiait uniquement `api_key == "dummy"`. Avec notre fausse clé CI
`sk-ant-test-ci-key`, le test ne skippait pas → échec.

Solution : `-m "not integration"` dans la commande pytest CI. Les tests
d'intégration tournent localement avec une vraie clé, pas en CI.

### Cache

- uv : `cache-dependency-glob: "backend/uv.lock"` via `astral-sh/setup-uv@v3`
- npm : `cache: "npm"` via `actions/setup-node@v4`
- cargo : `Swatinem/rust-cache@v2` avec `workspaces: "frontend/src-tauri -> target"`

### README mis à jour

- Badge CI corrigé : `vibe-ide` → `vibe_ide` (nom réel du repo)
- Badges TypeScript + Tauri ajoutés
- Table des fonctionnalités mise à jour (frontend ✅, Tauri ✅)
- Architecture diagram mis à jour
- Commandes `dev-frontend`, `tauri-dev`, `tauri-build`, `npm run test` ajoutées

## Résultats CI (run #27882715392)

```
Backend (pytest)      ✅  ubuntu-latest
Frontend (tsc+vitest) ✅  ubuntu-latest
Tauri (cargo check)   ✅  macos-latest
```
