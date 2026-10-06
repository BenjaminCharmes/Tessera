---
agent: codeur
created: 2026-10-05
depends_on: []
estimated_days: 1
id: ticket-353
pr_number: null
priority: high
status: done
title: Streamed tokens are batched per frame and a run's event history is bounded
type: fix
---

# ticket-353 — Les tokens sont regroupés par image et l'historique d'un run est borné

## Objectif

Qu'un agent qui streame ne déclenche plus une mise à jour d'état par token, et
que l'état d'un run ne grossisse plus sans fin : l'interface ne ralentit plus
à mesure que les runs durent.

## Contexte

`applyEvent` (`frontend/src/hooks/streamState.ts`) ajoute **chaque**
événement à `s.events` (ligne `const events = [...s.events, ev]`) et à
`s.ticketEvents`, `agent_token` compris, en recopiant le tableau entier. Rien
ne le borne, et le mode file garde tout d'un ticket à l'autre. Le texte des
tokens est déjà accumulé ailleurs, dans `entries[…].tokens`.

`useSupervision` (`frontend/src/hooks/useSupervision.ts`) appelle `setEtats`
puis `setRuns` pour chaque message de la WebSocket : avec plusieurs runs qui
streament, ce sont des centaines de mises à jour de l'état racine par seconde.

Les consommateurs de `events` lisent des événements de contrôle
(`pipeline_done`, `run_closed`, `queue_progress` — `issueDuRun.ts`,
`RunCard.tsx`, `useCockpit.ts`, `BottomPanel`), jamais `agent_token`.

## Solution proposée

1. **`agent_token` ne va plus dans `events` ni `ticketEvents`** : il ne met
   à jour que `entries[…].tokens`, comme aujourd'hui.
2. **Borne** : au-delà de `MAX_EVENTS = 2000` événements, les plus anciens
   sont retirés, sauf les événements de contrôle (`pipeline_done`,
   `run_closed`, `queue_progress`, `pipeline_start`) qui restent toujours.
3. **Regroupement par image** dans `useSupervision` : les messages reçus sont
   mis en file et appliqués ensemble une fois par `requestAnimationFrame`
   (repli `setTimeout(…, 16)` hors navigateur), en **un seul** `setEtats` et
   un seul `setRuns` par lot. L'ordre d'application reste celui de réception.
   Un `snapshot` vide d'abord la file en attente.

## Critères d'acceptation

- [ ] Un test de `streamStateFile.test.ts` (ou d'un nouveau
      `streamState.test.ts`) montre qu'un `agent_token` du codeur allonge
      `entries[…].tokens` sans ajouter d'élément à `events` ni à
      `ticketEvents`
- [ ] Un test montre qu'après 2 500 événements ordinaires, `events` en garde
      2 000, et qu'un `pipeline_done` reçu au début y figure toujours
- [ ] Un test de `useSupervision.test.ts` montre que cinquante messages reçus
      dans la même image ne produisent qu'un rendu du consommateur
- [ ] Un test de `useSupervision.test.ts` montre que l'état final après un lot
      est identique à celui obtenu en appliquant les messages un par un
- [ ] Les tests existants de `useSupervisionReplay.test.ts` et
      `useSupervisionReconnexion.test.ts` restent verts sans être modifiés,
      hors attente d'une image

## Dépendances

Aucune. Le ticket-354 s'appuie dessus.

## Estimation

Une journée.

## Risques

Les tests qui envoient un message puis lisent l'état aussitôt devront avancer
d'une image (faux timers) : c'est le seul ajustement admis sur les tests
existants.