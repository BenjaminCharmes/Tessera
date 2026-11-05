---
id: ticket-815
title: "The delivery modules move to services/livraison"
type: refactor
status: todo
pr_number: null
priority: low
agent: codeur
depends_on: [ticket-814]
estimated_days: 1
created: 2026-11-05
---

# ticket-815 — Les modules de livraison passent dans `services/livraison/`

## Objectif

Les vingt-neuf modules du domaine `livraison` (rebase, PR, CI, merge, surveillance) vivent dans
`services/livraison/`, à comportement constant.

## Contexte

ADR-075 ; section `livraison` de `memory/services-domaines.md`. C'est un des deux plus gros
déplacements, et le plus touché par les tickets récents (781, 787, 788, 792) : il se lance quand
aucune PR du projet n'est ouverte, sinon le rebase de la PR en cours entre en conflit avec les
renommages. Les portes de livraison (ADR-029, 030, 033, 039, 051, 065, 069) ne bougent pas.

## Ce que le ticket fait

- Lance `scripts/deplacer_domaine.py livraison`, relit le diff, lance la suite.
- Relit les tests de livraison, qui patchent le plus par chaîne.

## Critères d'acceptation

- [ ] Les vingt-neuf modules de la section `livraison` sont sous `services/livraison/`, aucun
      n'est resté à plat
- [ ] `livraison.py` est devenu `services/livraison/livraison.py`, ses importeurs aussi
- [ ] `A_DEPLACER` n'a plus d'entrée `livraison`, `ECARTS_DOMAINES` n'a grandi d'aucune ligne
- [ ] Aucune occurrence des anciens chemins pointés ne reste dans `backend/src`, `backend/tests`,
      `scripts/`, `Makefile`
- [ ] Le diff n'est que des renommages et des lignes d'import ou de chaîne ; la suite passe

## Ce que ça ne fait pas

Aucun changement de comportement, aucune porte de livraison modifiée.

## Risques

Le test de livraison réelle (PR, CI) ne se rejoue pas dans le run : après le merge, regarder la
première livraison suivante avant de lancer le ticket-816.
