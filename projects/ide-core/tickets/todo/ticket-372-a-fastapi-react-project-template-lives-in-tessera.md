---
id: ticket-372
title: "A versioned FastAPI + React project template lives in Tessera, and its test suite passes as created"
type: feat
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-10-07
---

# ticket-372 — Un gabarit de projet FastAPI + React versionné dans Tessera

## Objectif

Que le squelette back + front d'un nouveau projet vienne d'un gabarit unique,
versionné dans Tessera, au lieu d'être recopié d'un projet existant.

## Contexte

Chaque projet piloté par Tessera (habit-tracker, homelab-monitor,
repo-health, affut…) s'est monté à la main en recopiant le squelette d'un
autre : `pyproject.toml`, `conftest.py` avec le stub `jiter` (WDAC bloque
l'extension Rust sous Windows, ticket-016 de ces projets), `tsconfig*.json`,
`eslint.config.js`, `vitest.config.ts`, `vite.config.ts`. Les copies
divergent, et chaque nouveau projet rejoue la même demi-journée.

Le squelette de référence est celui de `projects/habit-tracker/` (backend
`app/` FastAPI + `tests/`, frontend React 19 + Vite + Tailwind v4 + Vitest).

## Solution proposée

Un dossier `templates/fastapi-react/` à la racine de Tessera, contenant un
squelette minimal et neutre :

- `backend/` : `pyproject.toml` (FastAPI, uvicorn ; dev : pytest, mypy),
  `conftest.py` avec le stub `jiter` repris de habit-tracker,
  `app/main.py` exposant `GET /api/health` → `{"status": "ok"}`,
  `tests/test_health.py` ;
- `frontend/` : `package.json` avec les scripts `dev`, `build`, `typecheck`,
  `lint`, `test`, les configurations TypeScript, ESLint, Vitest et Vite,
  `src/App.tsx` et `src/App.test.tsx` ;
- les valeurs propres au projet sont des marqueurs à remplacer :
  `{{project_id}}`, `{{project_name}}`, `{{backend_port}}`,
  `{{frontend_port}}` (dans `vite.config.ts` : port du serveur et proxy
  `/api` vers le backend).

Aucun `node_modules/`, `dist/`, `.venv/`, `uv.lock` ni base de données dans
le gabarit.

## Critères d'acceptation

- [ ] `templates/fastapi-react/backend/conftest.py` contient le stub `jiter` de `projects/habit-tracker/backend/conftest.py`
- [ ] `templates/fastapi-react/frontend/vite.config.ts` utilise `{{frontend_port}}` pour le port du serveur et `{{backend_port}}` pour le proxy `/api`
- [ ] Un test de `backend/tests/test_gabarit_fastapi_react.py` vérifie que le gabarit ne contient ni `node_modules`, ni `dist`, ni `.venv`, ni `uv.lock`, ni fichier `.db`
- [ ] Un test de `backend/tests/test_gabarit_fastapi_react.py` vérifie que chaque marqueur `{{…}}` du gabarit fait partie des quatre marqueurs listés
- [ ] Un test marqué `integration` de `backend/tests/test_gabarit_fastapi_react.py` copie le gabarit dans un dossier temporaire en remplaçant les marqueurs, installe les dépendances (`uv sync --extra dev`, `npm install`) et vérifie que typecheck, lint, test et build frontend, puis mypy et pytest backend sortent en 0

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Le test d'intégration installe des paquets : il est marqué `integration`,
donc exclu de la suite par défaut et de la CI, et se lance à la main avant
merge.

## Ce que ça ne fait pas

- Ne crée aucun projet : le ticket-373 instancie le gabarit.
- Ne contient pas de `CLAUDE.md` de projet : il s'écrit à la main.
