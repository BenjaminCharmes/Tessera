---
id: ticket-551
title: "Deleting a run worktree no longer freezes the backend"
type: fix
status: done
pr_number: null
priority: critical
agent: codeur
depends_on: []
estimated_days: 0.1
created: 2026-10-23
---

# ticket-551 — La suppression d'un worktree ne gèle plus le backend

## Objectif
Qu'à la fin d'un run en worktree, le backend continue de répondre pendant
que le dossier du worktree se vide.

## Contexte
Le 23/10 vers 10 h 30, à la fin du run c8f22395 (Kadoomi, ticket-105), le
8100 a cessé de répondre : `/health` en plus de 30 s, sockets en
`CLOSE_WAIT`. `supprimer()` de `services/run_worktree.py` vide ce que
`git worktree remove` laisse (le `node_modules` de pnpm, ticket-531) avec un
`shutil.rmtree` **synchrone** dans une fonction `async` : la boucle
d'événements reste bloquée toute la durée de la suppression, plusieurs
minutes pour un `node_modules`. Chaque run de Kadoomi, premier projet en
worktree, le reproduit.

## Solution
`await asyncio.to_thread(shutil.rmtree, …)`. Le test d'ordre
(`test_run_worktree_ordre.py`) reconnaît aussi cette forme d'appel comme une
suppression, pour que la règle « délier avant de supprimer » reste vérifiée.

Fait à la main (correctif isolé).

## Critères d'acceptation
- [x] Un test montre que `shutil.rmtree` de `supprimer()` s'exécute hors du thread de la boucle d'événements
- [x] `_noeuds_de_suppression` de `test_run_worktree_ordre.py` compte `asyncio.to_thread(shutil.rmtree, …)` comme une suppression, et un test le vérifie
- [x] Les tests existants de `run_worktree` passent

## Ce que ça ne fait pas
- Ne touche pas aux autres `shutil.rmtree` synchrones (`git_clone.py`,
  `project_removal.py`, `temporary_worktree.py`) : ils ne visent pas un
  `node_modules` en fin de run. À revoir si l'un d'eux gèle à son tour.
