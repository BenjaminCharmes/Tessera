---
agent: codeur
created: 2026-10-06
depends_on: []
estimated_days: 0.25
id: ticket-363
pr_number: null
priority: medium
status: done
title: Frontend tests allow for a loaded machine instead of timing out at 5 seconds
type: fix
---

# ticket-363 — Les tests frontend tolèrent une machine chargée

## Objectif

Qu'un ticket ne soit plus bloqué par un test frontend qui dépasse le délai
par défaut de vitest parce que la machine est occupée, et non parce que le
code est faux.

## Contexte

Le 2026-10-06, deux files tournaient en parallèle (ide-core et carriere), et
`scripts/verifier.py` lance déjà pytest et vitest en même temps
(ticket-351). Le ticket-360 a été bloqué après trois tours, chaque fois sur
un test différent : `ChatPanel.test.tsx`, `RunHistory`, puis
`AgentDetail.test.tsx` (« Test timed out in 5000ms »). Aucun ne touchait au
code du ticket, qui était purement backend. Relancé machine calme, le même
ticket est passé au premier tour.

`frontend/vite.config.ts` ne déclare aucun délai : vitest applique ses
5 secondes par défaut, aux tests comme aux hooks.

## Solution proposée

Déclarer dans la section `test` de `frontend/vite.config.ts` un délai de
15 secondes pour les tests et pour les hooks. Un test réellement bloqué
échoue toujours, plus tard ; un test lent sous charge passe.

## Critères d'acceptation

- [ ] `frontend/vite.config.ts` déclare `testTimeout: 15000` dans sa section `test`
- [ ] `frontend/vite.config.ts` déclare `hookTimeout: 15000` dans sa section `test`
- [ ] Aucun fichier de test n'est modifié

## Dépendances

Aucune.

## Estimation

0,25 jour.

## Risques

Un test qui se bloque met 15 secondes à échouer au lieu de 5. C'est le prix
d'un verdict qui ne dépend plus de la charge.

## Ce que ça ne fait pas

- Ne traite pas l'échec backend isolé du ticket-353 (tour 3, un test sur
  plus de mille, non reproduit) : sans trace, pas de correctif.
- Ne change pas l'ordre ni le parallélisme de `scripts/verifier.py`.