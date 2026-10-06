---
agent: codeur
created: 2026-10-05
depends_on:
- ticket-353
estimated_days: 1.5
id: ticket-354
plan: true
pr_number: null
priority: high
status: done
title: Run state lives in a store that components subscribe to, so one run's event
  re-renders only what shows it
type: refactor
---

# ticket-354 — L'état des runs vit dans un store, et un événement ne redessine que ce qui l'affiche

## Objectif

Qu'un événement d'un run ne redessine plus toute l'application — barre
latérale, kanban, chaque carte de ticket —, mais seulement les composants qui
affichent ce run.

## Contexte

`useSupervision` (`frontend/src/hooks/useSupervision.ts`) tient l'état de
tous les runs dans un seul objet `etats`, remonté jusqu'à `App` par
`useCockpit` (`frontend/src/hooks/useCockpit.ts`). `etatDe` dépend de
`[etats]` : son identité change à chaque événement, et tout ce qui le reçoit
se redessine, quel que soit le run concerné. Aucun composant de
`frontend/src/components/` n'utilise `React.memo`.

ADR-013 écarte Zustand et Jotai tant que l'état partagé tient dans
`useActiveProject` : la solution reste en React pur.

## Solution proposée

1. Un **store externe** minimal (`frontend/src/hooks/runStore.ts`) :
   état par `runId`, `subscribe(listener)`, `getSnapshot`, et un
   `appliquer(lot)` appelé par `useSupervision` (le lot du ticket-353).
   Pas de bibliothèque : `useSyncExternalStore` de React.
2. Des **sélecteurs** : `useEtatRun(runId)` ne redessine que si l'état de ce
   run a changé ; `useListeRuns()` ne redessine que si la liste des runs ou
   leur statut a changé (pas à chaque token).
3. `useCockpit` et `App` ne reçoivent plus `etats` ni un `etatDe` changeant :
   chaque composant qui affiche un run lit le store lui-même.
4. `React.memo` sur `Sidebar`, `TicketCard` et `KanbanView` (et leurs props
   rendues stables), qui n'affichent pas le flux d'un run.

## Critères d'acceptation

- [ ] `runStore.ts` existe et un test `runStore.test.ts` montre qu'un abonné
      à un run n'est pas notifié d'un événement d'un autre run
- [ ] Un test montre que `useListeRuns()` ne redessine pas son composant sur
      un `agent_token`, et le redessine sur un changement de statut
- [ ] Un test de `App.test.tsx` (ou d'un test d'écran équivalent) montre qu'un
      événement de run ne redessine pas une `TicketCard` (compteur de rendus)
- [ ] `useCockpit.ts` n'expose plus d'objet contenant l'état de tous les runs
- [ ] Les tests existants de `useSupervision*.test.ts` et
      `useCockpit.test.ts` passent, adaptés seulement à la nouvelle façon de
      lire l'état

## Dépendances

ticket-353 (lots d'événements à appliquer au store).

## Estimation

Une journée et demie.

## Risques

Refactor transversal : le tour de plan doit recenser tous les lecteurs de
`etats` / `etatDe` avant d'écrire. Garder le comportement visible identique —
c'est un changement de plomberie, pas d'écran.