---
id: ticket-817
title: "The worktree modules move to services/worktrees"
type: refactor
status: done
pr_number: null
priority: low
agent: codeur
depends_on: [ticket-816]
estimated_days: 1
created: 2026-11-05
---

# ticket-817 — Les modules de worktree passent dans `services/worktrees/`

## Objectif

Les huit modules du domaine `worktrees` (cycle de vie des worktrees de run) vivent dans
`services/worktrees/`, à comportement constant.

## Contexte

ADR-076 ; section `worktrees` de `memory/services-domaines.md`. Ces modules portent ADR-056 et
ADR-037 (un worktree avec du travail non commité ne se supprime pas) : aucune de ces portes ne bouge.

## Ce que le ticket fait

- Lance `scripts/deplacer_domaine.py worktrees`, relit le diff, lance la suite.

## Critères d'acceptation

- [x] Les huit modules de la section `worktrees` sont sous `services/worktrees/`, aucun n'est resté
      à plat
- [x] `A_DEPLACER` n'a plus d'entrée `worktrees`, `ECARTS_DOMAINES` n'a grandi d'aucune ligne
- [x] Aucune occurrence des anciens chemins pointés ne reste dans `backend/src`, `backend/tests`,
      `scripts/`, `Makefile`
- [x] Le diff n'est que des renommages et des lignes d'import ou de chaîne ; la suite passe

## Ce que ça ne fait pas

Aucun changement de comportement, aucun nettoyage de worktree.

## Risques

Aucun déplacement ne doit tourner pendant qu'un run de ce dépôt vit dans un worktree : ce ticket
s'exécute quand aucun autre run n'est ouvert.

## Notes de réalisation

Le domaine compte trois modules, pas huit : `scripts/domaines_services.py` fait foi (`worktree_dossiers` et `worktree_politique` sont dans `gardes`, la reprise des worktrees dans `pipeline`). `docs/architecture.md` suit le nouveau chemin de `run_worktree_populate` ; les documents historiques restent tels quels.
