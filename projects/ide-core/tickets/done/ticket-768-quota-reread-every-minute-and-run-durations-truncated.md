---
id: ticket-768
title: "The statistics quota is reread every minute and run durations truncate again"
type: fix
status: done
pr_number: null
priority: low
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-03
---

# ticket-768 — Le quota des statistiques se relit chaque minute et les durées de run tronquent à nouveau

## Objectif

Deux régressions discrètes des tickets 681 et 726 sont corrigées.

## Contexte

Audit du 30/10 (relecture du 03/11).
- `frontend/src/components/StatsView/index.tsx` passe à `useQuotaLu` un instant figé au
  montage : une seule lecture, alors que le commentaire dit « relu chaque minute ».
- `frontend/src/lib/format.ts` (notation `run`) arrondit là où l'ancien code de
  `HistoriqueView/runs.ts` et `RunHistory` tronquait : 119,6 s s'affiche « 2m 00s » au lieu
  de « 1m 59s ».

## Critères d'acceptation

- [x] Un test vérifie, avec une horloge simulée, que le quota est relu après une minute
- [x] Un test vérifie que la notation `run` affiche 119,6 s comme « 1m 59s »
