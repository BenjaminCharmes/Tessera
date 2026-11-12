---
agent: codeur
created: 2026-11-12
depends_on: []
estimated_days: 0.1
id: ticket-956
pr_number: null
priority: high
status: done
title: "Timing tests stay out of the pipeline tester and run in CI"
type: fix
---

# ticket-956 — Les tests chronométrés sortent du testeur du pipeline et restent en CI

## Objectif

Qu'un test qui mesure le temps de la machine ne bloque plus un run sans lien
avec lui.

## Contexte

Le 12/11, le run du ticket-950 a été bloqué au 3e tour par un seul test :
`test_usage_stats_responds_in_under_two_seconds_on_fifty_thousand_rows`
(6,5 s puis 5,8 s pour un seuil de 2 s). Le diff ne touchait pas
`usage_stats`, et le test passe seul. Le testeur tournait pendant que quatre
files (ide-core, curio, homelab-monitor, repo-health) occupaient la machine.

`scripts/verifier.py` est refusé en écriture aux agents (ADR-027, ADR-072) :
fait à la main.

## Solution

- Marqueur pytest `perf` déclaré dans `backend/pyproject.toml`
  (`[tool.pytest.ini_options]`, `markers`).
- `scripts/verifier.py` lance `-m "not integration and not perf"`.
- Le test de `backend/tests/test_usage_stats.py` porte `@pytest.mark.perf`.
- `.github/workflows/ci.yml` garde `-m "not integration"` : la CI, seule sur
  son runner, lance toujours le test chronométré.

## Critères d'acceptation

- [x] `backend/tests/test_verifier.py` : la commande pytest du vérificateur
      exclut `integration` et `perf`.
- [x] `pytest -m perf tests/test_usage_stats.py` sélectionne le test
      chronométré, qui passe seul.
- [x] Tests du vérificateur, de `usage_stats`, des consignes et des chemins
      protégés verts (118).

## Ce que ça ne fait pas

- Ne change pas le seuil de 2 s ni le code d'`usage_stats`.
- Ne traite pas le délai de démarrage des workers vitest sous charge
  (« Timeout waiting for worker to respond », vu au tour 2 du même run).
