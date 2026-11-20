---
agent: codeur
created: 2026-11-12
depends_on: []
estimated_days: 0.25
id: ticket-945
pr_number: null
priority: medium
status: done
title: "CI checkouts do not persist the GitHub token for the PR code"
type: chore
---

# ticket-945 — Les checkouts de la CI ne laissent pas le jeton GitHub au code de la PR

## Objectif

Que le code d'une PR exécuté par la CI (tests, E2E) ne puisse pas lire le
`GITHUB_TOKEN` du workflow.

## Contexte

Audit du 12/11 (F5). `.github/workflows/ci.yml` utilise `actions/checkout`
sans `persist-credentials: false` : le jeton reste dans le `.git/config` du
runner, lisible par les tests de la PR. `CI_RUNNER` n'est pas défini (vérifié
le 12/11 : `ubuntu-latest`), donc le risque reste borné au dépôt.

## Critères d'acceptation

- [x] Chaque `actions/checkout` de `.github/workflows/ci.yml` qui exécute le
      code de la PR porte `persist-credentials: false`.
- [x] Un test de `backend/tests/` lit les workflows et le vérifie.

## Ce que ça ne fait pas

- Ne change ni les déclencheurs ni `CI_RUNNER`. Aucun agent n'écrit dans
  `.github/workflows/` : ce ticket se fait à la main.
