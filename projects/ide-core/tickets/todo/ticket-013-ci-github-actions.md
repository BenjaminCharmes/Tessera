---
id: ticket-013
title: "CI — GitHub Actions (backend + frontend + tauri)"
type: chore
status: todo
priority: high
agent: codeur
depends_on:
  - ticket-012
created: 2026-06-20
---

# ticket-013 — CI GitHub Actions

## Contexte

Pas de CI sur le repo. Chaque push sur main pourrait casser le backend, le
frontend ou la compilation Rust sans qu'on le sache. Ce ticket ajoute un
pipeline GitHub Actions avec 3 jobs parallèles.

## Tâches

### 1. `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: ["**"]
  pull_request:
    branches: [main]

jobs:

  backend:
    name: Backend (pytest)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with:
          version: "latest"
      - name: Install dependencies
        run: cd backend && uv sync --extra dev
      - name: Run tests
        run: cd backend && uv run pytest -v
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}

  frontend:
    name: Frontend (tsc + vitest)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "24"
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json
      - name: Install dependencies
        run: cd frontend && npm ci
      - name: Type check
        run: cd frontend && npx tsc --noEmit
      - name: Unit tests
        run: cd frontend && npm run test

  tauri:
    name: Tauri (cargo check)
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
      - uses: Swatinem/rust-cache@v2
        with:
          workspaces: "frontend/src-tauri -> target"
      - name: Cargo check
        run: cd frontend/src-tauri && cargo check
```

### 2. Secrets GitHub à configurer

Dans `Settings > Secrets > Actions` du repo :

| Secret | Usage |
|--------|-------|
| `ANTHROPIC_API_KEY` | Tests backend qui appellent l'API (si applicable) |

Note : si les tests backend mockent tous les appels Anthropic, ce secret n'est
pas strictement nécessaire pour la CI. À vérifier.

### 3. `.github/` à créer dans le repo

```
.github/
  workflows/
    ci.yml
```

### 4. Badge CI dans `README.md`

Ajouter en haut du README :
```markdown
[![CI](https://github.com/BenjaminCharmes/vibe-ide/actions/workflows/ci.yml/badge.svg)](...)
```

## Critères d'acceptation

- [ ] `ci.yml` est créé dans `.github/workflows/`
- [ ] Job `backend` : `pytest` passe sur ubuntu-latest
- [ ] Job `frontend` : `tsc --noEmit` + `npm run test` passent
- [ ] Job `tauri` : `cargo check` passe sur macos-latest
- [ ] Les 3 jobs s'exécutent en parallèle
- [ ] Le cache npm/cargo réduit les temps de build
- [ ] Badge CI visible dans le README

## Notes

- Utiliser `macos-latest` pour Tauri (WKWebView headers disponibles)
- `ubuntu-latest` pour backend et frontend (plus rapide, pas de WebView nécessaire)
- Le job Tauri fait `cargo check`, pas `cargo build` — évite les 10+ min de
  compilation complète en CI
- Si les tests backend requièrent une vraie API key, ajouter `if: github.actor != 'dependabot'`
  sur les steps sensibles
