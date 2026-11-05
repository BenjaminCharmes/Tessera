---
id: ticket-807
title: "The agent modules move to services/agents"
type: refactor
status: todo
pr_number: null
priority: low
agent: codeur
depends_on: [ticket-806]
estimated_days: 1
created: 2026-11-05
---

# ticket-807 — Les modules d'agent passent dans `services/agents/`

## Objectif

Les six modules du domaine `agents` (registre, exécution d'un agent, chat) vivent dans
`services/agents/`, à comportement constant.

## Contexte

ADR-074 ; section `agents` de `memory/services-domaines.md`. Ne pas confondre avec le paquet
`tessera/agents/`, qui disparaît au ticket-810.

## Ce que le ticket fait

- Lance `scripts/deplacer_domaine.py agents`, relit le diff, lance la suite.

## Critères d'acceptation

- [ ] Les six modules de la section `agents` sont sous `services/agents/`, aucun n'est resté à plat
- [ ] `A_DEPLACER` n'a plus d'entrée `agents`, `ECARTS_DOMAINES` n'a grandi d'aucune ligne
- [ ] Aucune occurrence des anciens chemins pointés ne reste dans `backend/src`, `backend/tests`,
      `scripts/`, `Makefile`
- [ ] `tessera/agents/github_sync.py` n'est pas touché (ticket-810)
- [ ] Le diff n'est que des renommages et des lignes d'import ou de chaîne ; la suite passe

## Ce que ça ne fait pas

Aucun changement de comportement. Le paquet `tessera/agents/` reste en place.

## Risques

Les chemins `tessera.agents` et `tessera.services.agents` coexistent jusqu'au ticket-810 : le
script ne doit réécrire que `tessera.services.<module>`.
