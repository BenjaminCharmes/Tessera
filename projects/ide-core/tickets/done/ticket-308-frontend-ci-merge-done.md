---
agent: codeur
created: 2026-10-02
depends_on:
- ticket-307
estimated_days: 0.5
id: ticket-308
pr_number: 210
priority: medium
status: done
title: A closed run's card says its PR is waiting for CI, then merged or blocked
type: feat
---

# ticket-308 — La carte d'un run clos suit la CI de sa PR

## Objectif

Après le ticket-307, `run_closed` arrive avant le merge. La carte du run doit
montrer que la livraison continue, puis comment elle a fini.

## Contexte

ADR-051, ADR-041. `ci_merge_done` arrive sur le canal d'observation après la
clôture du run, sans run vivant associé. La carte d'un run clos reste dans la
Supervision jusqu'à ce qu'on la ferme (ticket-279) : c'est là qu'il faut
l'afficher.

## Critères d'acceptation

- [ ] `ci_merge_done` est déclaré dans les types d'événements du frontend
- [ ] Un test vérifie qu'une carte de run clos, qui a reçu `livraison_done`
      avec un `pr_number` mais pas encore `ci_merge_done`, affiche « PR #N —
      en attente de CI »
- [ ] Un test vérifie que `ci_merge_done` avec `merged: true` affiche « PR #N
      mergée »
- [ ] Un test vérifie que `ci_merge_done` avec `merged: false` affiche
      l'`arret`
- [ ] Un test vérifie que `ci_merge_done` d'un projet est rattaché à la carte
      du bon `ticket_id`, et non à la dernière carte reçue
- [ ] Les couleurs restent celles d'ADR-026 : `amber` pour l'attente, `green`
      pour le succès, `red` pour l'échec

## Dépendances

ticket-307 (l'événement existe côté backend).

## Périmètre

`frontend/src/components/SupervisionView/`, `frontend/src/hooks/`
(`supervisionEvents`, `streamState`), `frontend/src/types/api.ts`.