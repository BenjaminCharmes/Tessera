---
id: ticket-812
title: "The verdict modules move to services/verdicts"
type: refactor
status: todo
pr_number: null
priority: low
agent: codeur
depends_on: [ticket-811]
estimated_days: 1
created: 2026-11-05
---

# ticket-812 — Les modules de verdict passent dans `services/verdicts/`

## Objectif

Les douze modules du domaine `verdicts` (reviewer, audit sécurité, validateur) vivent dans
`services/verdicts/`, à comportement constant.

## Contexte

ADR-076 ; section `verdicts` de `memory/services-domaines.md`. Ces modules portent des portes qui
échouent fermées (ADR-039, ADR-061) : le déplacement ne doit en changer aucune.

## Ce que le ticket fait

- Lance `scripts/deplacer_domaine.py verdicts`, relit le diff, lance la suite.

## Critères d'acceptation

- [ ] Les douze modules de la section `verdicts` sont sous `services/verdicts/`, aucun n'est resté
      à plat
- [ ] `A_DEPLACER` n'a plus d'entrée `verdicts`, `ECARTS_DOMAINES` n'a grandi d'aucune ligne
- [ ] Aucune occurrence des anciens chemins pointés ne reste dans `backend/src`, `backend/tests`,
      `scripts/`, `Makefile`
- [ ] Le diff n'est que des renommages et des lignes d'import ou de chaîne ; la suite passe

## Ce que ça ne fait pas

Aucun changement de comportement, aucun schéma de verdict touché.

## Risques

Les tests de ces modules patchent beaucoup par chaîne : un patch non réécrit désarme un test de
porte sans le faire échouer. Relire chaque `tessera.services.<module>` restant avec `grep`.
