---
agent: codeur
created: 2026-10-02
depends_on: []
estimated_days: 1
id: ticket-305
pr_number: null
priority: high
status: done
title: 'Delivery splits in two: rebase, push and PR in the run, CI and merge after
  it'
type: feat
---

# ticket-305 — La livraison se scinde : rebase, push et PR dans le run

## Objectif

Extraire la première phase de `LivraisonService.livrer()` dans une méthode
`livrer_phase_1()`, qui s'arrête après l'ouverture de la PR et rend le
`pr_number`. La phase 2 (attente de CI, merge) vivra dans `CIWatcher`
(ticket-306).

## Contexte

ADR-051 scinde la livraison. Aujourd'hui, `livrer()` attend la CI pendant
environ quatre minutes (médiane mesurée par le ticket-288), et le projet
reste verrouillé pendant tout ce temps. L'objectif est que `run_pipeline`
appelle `livrer_phase_1`, libère le verrou, puis confie la phase 2 à
`CIWatcher`.

`livrer()` reste disponible pour les appels hors pipeline : elle enchaîne
`livrer_phase_1` puis `livrer_phase_2`.

## Critères d'acceptation

- [ ] `LivraisonService` expose `livrer_phase_1()`, qui rend une `Livraison`
      avec `pr_number`, et `livrer_phase_2(pr_number)`, qui rend une
      `Livraison` avec `merged`
- [ ] `livrer()` enchaîne la phase 1 puis la phase 2, et les tests existants
      de `test_livraison.py` passent sans modification
- [ ] Un test vérifie que `livrer_phase_1()` produit les mêmes `etapes` et
      `durees_ms` que l'actuel `livrer()` jusqu'à l'ouverture de la PR
- [ ] Un test vérifie qu'un rebase en conflit arrête la phase 1 avec un
      `arret`, sans PR
- [ ] Un test vérifie que sur `autonomy: commit`, la phase 1 ne pousse rien

## Dépendances

Aucune (ADR-051 est en vigueur depuis le ticket-291).

## Périmètre

`backend/src/tessera/services/livraison.py` et ses tests.