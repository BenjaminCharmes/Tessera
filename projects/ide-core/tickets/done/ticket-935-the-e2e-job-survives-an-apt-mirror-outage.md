---
agent: codeur
created: 2026-11-11
depends_on: []
estimated_days: 0.1
id: ticket-935
pr_number: null
priority: medium
status: done
title: "The E2E job survives an apt mirror outage"
type: fix
---

# ticket-935 — Le job E2E survit à une panne des miroirs apt

## Objectif

Qu'une panne des miroirs Ubuntu ne fasse plus échouer l'E2E de toutes les PR.

## Contexte

Le 11/11 après-midi, l'étape « Install Playwright browsers (Linux) » de
`.github/workflows/ci.yml` (`npx playwright install --with-deps chromium`) a
échoué sur cinq PR de suite (`Installation process exited with code: 100`,
index apt non téléchargés), relances comprises. Le CIWatcher ne mergeait plus
rien, et les PR d'interface 918 et 919 restaient sans E2E.

Fait **à la main** : `.github/workflows/` est refusé à tout agent.

## Ce qui est fait

Si l'installation avec `--with-deps` échoue, l'étape installe Chromium seul,
avec un avertissement dans le journal : l'image Ubuntu des runners GitHub
porte déjà ses bibliothèques système.

## Critères d'acceptation

- [x] `.github/workflows/ci.yml` retombe sur `npx playwright install chromium`
      quand `--with-deps` échoue.
- [x] L'E2E de la PR passe pendant la panne.
