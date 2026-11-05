---
id: ticket-812
title: "The usage modules move to services/usage"
type: refactor
status: todo
pr_number: null
priority: low
agent: codeur
depends_on: [ticket-811]
estimated_days: 1
created: 2026-11-05
---

# ticket-812 — Les modules d'usage passent dans `services/usage/`

## Objectif

Les huit modules du domaine `usage` (coûts, quotas, appels d'agent) vivent dans `services/usage/`,
à comportement constant.

## Contexte

ADR-074 ; section `usage` de `memory/services-domaines.md`. `providers/` importe `agent_calls`,
`cost_calculator` et `quota_tracker` : `usage` est de rang plus bas, le sens est permis.

## Ce que le ticket fait

- Lance `scripts/deplacer_domaine.py usage`, relit le diff, lance la suite.
- Vérifie à la main `scripts/mesure_calculs.py`, qui importe `cost_calculator`.

## Critères d'acceptation

- [ ] Les huit modules de la section `usage` sont sous `services/usage/`, aucun n'est resté à plat
- [ ] `A_DEPLACER` n'a plus d'entrée `usage`, `ECARTS_DOMAINES` n'a grandi d'aucune ligne
- [ ] Aucune occurrence des anciens chemins pointés ne reste dans `backend/src`, `backend/tests`,
      `scripts/`, `Makefile`
- [ ] Le diff n'est que des renommages et des lignes d'import ou de chaîne ; la suite passe

## Ce que ça ne fait pas

Aucun changement de comportement, aucun calcul de coût modifié.

## Risques

Le calcul de coût est testé par chaîne dans plusieurs fichiers : relire les restes de
`tessera.services.cost_calculator` et `tessera.services.quota_tracker` avec `grep`.
