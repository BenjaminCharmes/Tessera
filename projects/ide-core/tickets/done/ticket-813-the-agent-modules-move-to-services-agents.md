---
id: ticket-813
title: "The agent modules move to services/agents"
type: refactor
status: done
pr_number: null
priority: low
agent: codeur
depends_on: [ticket-812]
estimated_days: 1
created: 2026-11-05
---

# ticket-813 — Les modules d'agent passent dans `services/agents/`

## Objectif

Les six modules du domaine `agents` (registre, exécution d'un agent, chat) vivent dans
`services/agents/`, à comportement constant.

## Contexte

ADR-076 ; section `agents` de `memory/services-domaines.md`. Ne pas confondre avec le paquet
`tessera/agents/`, qui disparaît au ticket-816.

## Ce que le ticket fait

- Lance `scripts/deplacer_domaine.py agents`, relit le diff, lance la suite.

## Critères d'acceptation

- [x] Les six modules de la section `agents` sont sous `services/agents/`, aucun n'est resté à plat
- [x] `A_DEPLACER` n'a plus d'entrée `agents`, `ECARTS_DOMAINES` n'a grandi d'aucune ligne
- [x] Aucune occurrence des anciens chemins pointés ne reste dans `backend/src`, `backend/tests`,
      `scripts/`, `Makefile`
- [x] `tessera/agents/github_sync.py` n'est pas touché (ticket-816)
- [x] Le diff n'est que des renommages et des lignes d'import ou de chaîne ; la suite passe

## Ce que ça ne fait pas

Aucun changement de comportement. Le paquet `tessera/agents/` reste en place.

## Risques

Les chemins `tessera.agents` et `tessera.services.agents` coexistent jusqu'au ticket-816 : le
script ne doit réécrire que `tessera.services.<module>`.

## Notes de réalisation

Six modules, comme annoncé. L'écart connu `services/chat_suggestion.py -> pipeline` de `ECARTS_DOMAINES` suit le module (`services/agents/chat_suggestion.py`), sans ligne ajoutée. Seuls des documents historiques citent les anciens chemins : ils restent tels quels.
