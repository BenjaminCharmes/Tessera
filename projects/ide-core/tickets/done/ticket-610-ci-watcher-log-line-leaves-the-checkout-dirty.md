---
agent: codeur
created: 2026-10-27
depends_on: []
estimated_days: 0.5
id: ticket-610
pr_number: null
priority: high
status: done
title: 'A blocked merge no longer leaves the checkout dirty: the next ticket commits
  the pipeline log line instead of failing'
type: fix
---

# ticket-610 — Une ligne de journal du CIWatcher ne bloque plus la file

## Objectif

Qu'une PR non mergée par `CIWatcher` n'arrête plus le ticket suivant de la
file sur un arbre sale.

## Contexte

Le 27/10 à 17 h 47, la file ide-core s'est arrêtée sur le ticket-569 sans qu'il
ait commencé :

```
git rebase 92c0a5ee…
error: Your local changes to the following files would be overwritten by checkout:
	projects/ide-core/memory/pipeline-log.md
```

Ce qui s'est passé : la PR du ticket-577 était en conflit avec `develop`.
`CIWatcher._ecrire_log_blocage` (`backend/src/tessera/services/ci_watcher.py`)
a écrit « livraison: arrêt — PR #691 non mergée… » dans
`memory/pipeline-log.md` du checkout. Pour un projet sans worktree,
`orchestrator.py` lui passe ce chemin (`pipeline_log_path_ci`). La phase 2
tourne en fond, après le commit du ticket : la ligne reste non commitée. Le
ticket suivant, repris sur sa branche existante, tente un rebase, que git
refuse. Le ticket est compté non approuvé et toute la file s'interrompt.

ADR-018 et ADR-037 posent que l'arbre ne reste jamais sale ; ADR-039 permet déjà
aux commits de rangement du pipeline (`tickets/**`, `memory/pipeline-log.md`)
de suivre une approbation.

## Solution proposée

Avant toute création, reprise ou rebase de branche d'un ticket, si les seules
modifications non commitées du checkout sont dans `memory/pipeline-log.md`,
le pipeline les emporte : il les commite sur la branche du ticket, avec le
message de rangement habituel, une fois la branche en place. Pour cela, il les
met de côté le temps du changement de branche (le contenu est relu, puis
réécrit), et non par `git stash`, partagé entre les worktrees.

Toute autre modification non commitée garde le comportement actuel.

## Critères d'acceptation

- [ ] Un test de `backend/tests/` reproduit le cas : checkout dont seul `memory/pipeline-log.md` est modifié, ticket repris sur une branche existante en retard sur la base ; le rebase réussit et la ligne se retrouve commitée sur la branche du ticket.
- [ ] Un test vérifie qu'une modification d'un autre fichier que `memory/pipeline-log.md` fait toujours échouer la préparation de la branche, comme aujourd'hui.
- [ ] Le diff n'appelle `git stash` nulle part.
- [ ] Le commit qui emporte la ligne porte le message de rangement du pipeline déjà utilisé pour `memory/pipeline-log.md`.

## Ce que ça ne fait pas

- Ne déplace pas l'écriture du CIWatcher hors du dépôt : la ligne reste
  utile dans le journal du projet.
- Ne change rien pour un projet en `worktree` : `pipeline_log_path_ci` y vaut
  déjà `None`.