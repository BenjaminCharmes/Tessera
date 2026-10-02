---
id: ticket-308
title: "Frontend : afficher CI_MERGE_DONE et les livraisons en cours"
type: feat
status: todo
priority: medium
agent: codeur
---

# ticket-308 — Frontend : afficher CI_MERGE_DONE et les livraisons en cours

## Objectif

Après ticket-307, `run_closed` arrive avant le merge. L'UI doit montrer que
la livraison continue en arrière-plan. Un événement `CI_MERGE_DONE` sur le
canal projet (ADR-041) signale la fin.

## Contexte

ADR-051, ADR-041. Le canal WebSocket reçoit déjà tous les événements du run.
`CI_MERGE_DONE` n'est lié à aucun run actif : il arrive sur le canal global
après que le run est clos.

## Critères d'acceptation

- [ ] `EventType.CI_MERGE_DONE` ajouté côté frontend (`types/api.ts`)
- [ ] Le `RunView` affiche un bandeau "livraison en attente de CI" entre
      `LIVRAISON_DONE` (PR ouverte) et `CI_MERGE_DONE`
- [ ] `CI_MERGE_DONE` avec `merged: true` referme le bandeau et affiche
      "mergée" ; `merged: false` affiche l'`arret`
- [ ] Le bandeau utilise uniquement les couleurs d'ADR-026 (amber pendant
      l'attente, green sur succès, red sur échec)
- [ ] Tests Vitest couvrent les trois états (attente, mergée, échec)
- [ ] `npm run build` et `tsc --noEmit` passent

## Dépendances

ticket-307 (l'événement existe en backend)

## Périmètre

`frontend/src/components/RunView/`,
`frontend/src/types/api.ts`.
