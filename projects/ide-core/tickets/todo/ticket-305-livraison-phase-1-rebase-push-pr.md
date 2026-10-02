---
id: ticket-305
title: "Scinder LivraisonService : rebase + push + PR dans le run"
type: feat
status: todo
priority: high
agent: codeur
---

# ticket-305 — Scinder LivraisonService : rebase + push + PR dans le run

## Objectif

Extraire la première phase de `LivraisonService.livrer()` dans une méthode
`livrer_phase_1()` qui s'arrête après l'ouverture de la PR et retourne le
`pr_number`. La phase 2 (attente CI, merge) vit dans `CIWatcher` (ticket-306).

## Contexte

ADR-051 scinde la livraison. `livrer()` bloque 15 min sur `_attendre_la_ci`.
L'objectif est que `run_pipeline` appelle `livrer_phase_1`, libère le verrou,
puis confie la phase 2 à `CIWatcher`.

La méthode existante `livrer()` reste pour les appels hors pipeline (tests,
appels directs) — elle enchaîne `livrer_phase_1` + phase 2 en séquence.

## Critères d'acceptation

- [ ] `LivraisonService` expose `livrer_phase_1()` → `Livraison` (avec
      `pr_number`, sans `merged`) et `livrer_phase_2(pr_number)` → `Livraison`
- [ ] `livrer()` reste compatible : enchaîne phase 1 puis phase 2
- [ ] Tous les tests existants de `LivraisonService` passent sans modification
- [ ] `LivraisonService.livrer_phase_1()` émet les mêmes `etapes` / `durees_ms`
      que l'actuel `livrer()` jusqu'à l'ouverture de la PR
- [ ] Un test unitaire couvre `livrer_phase_1` (rebase OK → PR ouverte → retourne
      `Livraison` avec `pr_number` et `arret=None`)
- [ ] Un test couvre le court-circuit sur `autonomy: commit` (pas de phase 1)

## Dépendances

ticket-291 (ADR-051 en vigueur)

## Périmètre

`backend/src/tessera/services/livraison.py` uniquement.
