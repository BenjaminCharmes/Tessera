---
id: ticket-804
title: "The documentation modules move to services/documentation"
type: refactor
status: todo
pr_number: null
priority: low
agent: codeur
depends_on: [ticket-803]
estimated_days: 1
created: 2026-11-05
---

# ticket-804 — Les modules de documentation passent dans `services/documentation/`

## Objectif

Les douze modules du domaine `documentation` vivent dans `services/documentation/`, à comportement
constant.

## Contexte

ADR-074 ; section `documentation` de `memory/services-domaines.md`. Le module `documentation.py`
et le dossier portent le même nom : l'import devient `tessera.services.documentation.documentation`.

## Ce que le ticket fait

- Lance `scripts/deplacer_domaine.py documentation`, relit le diff, lance la suite.
- Vérifie que `from tessera.services import documentation` (le module) est devenu
  `from tessera.services.documentation import documentation`, et non l'import du paquet vide.

## Critères d'acceptation

- [ ] Les douze modules de la section `documentation` sont sous `services/documentation/`, aucun
      n'est resté à plat
- [ ] `A_DEPLACER` n'a plus d'entrée `documentation`, `ECARTS_DOMAINES` n'a grandi d'aucune ligne
- [ ] Aucune occurrence des anciens chemins pointés ne reste dans `backend/src`, `backend/tests`,
      `scripts/`, `Makefile`
- [ ] Le diff n'est que des renommages et des lignes d'import ou de chaîne ; la suite passe

## Ce que ça ne fait pas

Aucun changement de comportement, aucune édition des textes de documentation.

## Risques

Le nom du module égal au nom du dossier : un `import tessera.services.documentation as d` visait le
module et viserait désormais le paquet vide. Le script le signale ; le relire à la main.
