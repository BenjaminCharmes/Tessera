---
agent: codeur
created: 2026-11-11
depends_on: []
estimated_days: 0.25
id: ticket-920
pr_number: null
priority: medium
status: done
title: "Minor dependency updates and the transitive advisories they close"
type: chore
---

# ticket-920 — Mises à jour mineures des dépendances et alertes transitives

## Objectif

Remettre les dépendances à jour dans leurs plages déclarées et fermer les
alertes publiées sur des dépendances transitives, sans aucune majeure.

## Contexte

Audit du 11/11 (lecture seule) :

- backend, `pip-audit` : 8 alertes sur `anyio`, `certifi`, `pyjwt`,
  `opentelemetry-api`, toutes transitives ;
- frontend, `npm audit` : 0 alerte en production, 2 `high` en dev (`zod`,
  `browserslist`) ;
- plusieurs mineures en retard (`fastapi`, `uvicorn`, `pydantic`, `vite`,
  `vitest`, `tailwindcss`…).

Fait **à la main** : seuls les lockfiles changent, et un run ide-core tourne
dans le checkout du backend ; un `uv.lock` changé en cours de file ferait
resynchroniser le venv sous le backend en marche.

## Solution retenue

- `backend/uv.lock` : `uv lock --upgrade-package` sur une liste fermée
  (claude-agent-sdk, pydantic, pydantic-settings, uvicorn, fastapi, pytest,
  pytest-asyncio, anyio, certifi, pyjwt, opentelemetry-api). Pas de
  `--upgrade` global : `anthropic>=0.28.0` sauterait en 2.x.
- `frontend/package-lock.json` : `npm update --package-lock-only`, dans les
  plages de `package.json`.
- Ni `pyproject.toml` ni `package.json` ne changent. `mypy<1.19`,
  `ruff==0.14.3` et `rpds-py==2026.6.3` restent épinglés (Smart App Control).

## Critères d'acceptation

- [x] `pip-audit` ne relève plus `anyio`, `certifi`, `pyjwt` ni
      `opentelemetry-api`.
- [x] `npm audit` ne relève plus d'alerte `high`.
- [x] `uv sync`, `mypy src/` et pytest passent sur ce PC (Smart App Control
      compris).
- [x] La CI de la PR est verte (tsc, eslint, vitest, pytest).

## Ce que ça ne fait pas

- Laisse 10 alertes `moderate` sur `minimatch`, tirées par eslint en dev :
  `npm audit fix --force` rétrograderait eslint en 9.x.
- Aucune majeure : `anthropic` 2.x, `websockets` 17, `typescript` 7,
  `jsdom` 31 et `ruff` restent à faire, chacune à part.
