---
id: ticket-885
title: "The phase-1 delivery test proves the steps and durations in merge mode"
type: test
status: todo
pr_number: null
priority: low
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-11-06
---

# ticket-885 — The phase-1 delivery test proves the steps and durations in merge mode

## Objectif

Le test de la phase 1 de livraison vérifie ce que son nom promet, en autonomie `merge`.

## Contexte

Trouvé par l'essai de seconde revue (ticket-846, `docs/essais/seconde-revue.md`) : le reviewer l'a relevé sur un commit classé sain, un humain l'a confirmé, et le défaut est toujours sur `develop` le 06/11. Entrée s09, ticket-305.

Dans `backend/tests/test_livraison.py`, le test `test_phase_1_produit_memes_etapes_et…` tourne en autonomie `pr` pour ses deux appels et ne compare jamais `durees_ms`.

## Solution proposée

Le test passe en autonomie `merge` et compare les étapes et les durées de la phase 1 à celles de `livrer()`.

## Critères d'acceptation

- [ ] Le test de `backend/tests/test_livraison.py` sur la phase 1 déclare l'autonomie `merge`.
- [ ] Il vérifie que les étapes de la phase 1 sont le début des étapes de `livrer()`.
- [ ] Il vérifie que `len(durees_ms) == len(etapes)` pour la phase 1, et que ce nombre est inférieur à celui de `livrer()`.

## Dépendances

Aucune.

## Estimation

Une demi-journée au plus.

## Ce que ça ne fait pas

Ne revoit pas le reste du ticket d'origine : seulement le défaut confirmé.
