---
id: ticket-357
title: "The verifier runs the backend tests on several workers"
type: fix
status: done
pr_number: null
priority: critical
agent: codeur
depends_on: []
estimated_days: 0.25
created: 2026-10-05
---

# ticket-357 — Le vérificateur lance les tests backend sur plusieurs processus

## Objectif

Que la suite du testeur d'ide-core tienne dans son délai de 900 s.

## Contexte

Le 2026-10-05, le ticket-347 a été bloqué après trois tours, chacun coupé à
900 s par le testeur, sans qu'aucun test soit rouge. Mesuré le même jour :
`pytest` seul prend 12 min 05 en série (1 973 tests, dont les tests git qui
coûtent 5 à 70 s chacun sous Windows), le frontend 3 min 35 (tsc 17 s,
eslint 43 s, vitest 155 s). La suite dépassait donc son délai à elle seule,
avant même toute contention entre projets (ticket-348).

Avec `pytest-xdist` sur 8 processus : 1 973 tests verts en 2 min 32.

Fait à la main, hors pipeline : tant qu'il n'est pas livré, tout ticket
d'ide-core lancé dans le pipeline expire au testeur.

## Solution

- `pytest-xdist` rejoint l'extra `dev` de `backend/pyproject.toml`.
- `scripts/verifier.py` construit la commande pytest par `pytest_command()` :
  `-n 8` quand xdist est installé, en série sinon.

## Critères d'acceptation

- [x] `test_verifier.py` couvre la commande avec et sans xdist, et la
      présence de `pytest-xdist` dans `pyproject.toml`
- [x] La suite backend passe sur 8 processus (1 974 tests, 3 min 11)

## Ce que ça ne fait pas

- La CI garde son pytest en série : elle n'a pas de délai de 900 s.
- Les chaînes backend et frontend restent séquentielles : c'est le
  ticket-351.
