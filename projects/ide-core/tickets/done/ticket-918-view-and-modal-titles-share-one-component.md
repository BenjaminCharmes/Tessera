---
agent: codeur
created: 2026-11-11
depends_on: []
estimated_days: 0.5
id: ticket-918
pr_number: null
priority: low
status: done
title: View titles go through RegionTitle and modal titles through one shared title
type: refactor
---

# ticket-918 — Titres de vue par `RegionTitle`, titres de modale par un titre partagé

## Objectif

Une seule hiérarchie de titres dans l'interface.

## Contexte

La plupart des vues titrent par `design/RegionTitle.tsx`. Font exception :
`components/RituelsView/index.tsx` (un `<h1>` et un `<h2>` à la main) et
`components/HistoriqueView/DetailDuRun.tsx` (`<h1 text-xl>`).

`design/ui/Modale.tsx` n'a pas de titre : chaque modale recopie le sien, en
trois variantes (`text-base font-semibold`, `text-base font-medium`,
`text-xl font-semibold`).

Au passage, « Issue » calque l'anglais *outcome* :
`components/StatsView/RecentRuns.tsx` (colonne « Issue ») et
`components/StatsView/index.tsx` (« Issue des runs »).

## Solution proposée

- `RituelsView` et `DetailDuRun` titrent par `RegionTitle`.
- `design/ui/Modale.tsx` exporte un `TitreDeModale` (un `<h2>` au style
  unique) ; les modales qui recopient leur titre l'utilisent.
- « Issue » devient « Résultat ».

## Critères d'acceptation

- [ ] `components/RituelsView/index.tsx` et
      `components/HistoriqueView/DetailDuRun.tsx` importent `RegionTitle` et ne
      portent plus de `<h1>`.
- [ ] `design/ui/Modale.tsx` exporte `TitreDeModale`, et un test de
      `design/ui/Modale.test.tsx` vérifie qu'il rend un titre de niveau 2.
- [ ] Au moins cinq modales qui rendaient un `<h2>` de titre à la main
      importent `TitreDeModale` à sa place.
- [ ] `components/StatsView/RecentRuns.tsx` et `components/StatsView/index.tsx`
      disent « Résultat » au lieu d'« Issue ».
- [ ] Les tests de ces composants passent, adaptés aux nouveaux textes.

## Dépendances

Aucune.

## Estimation

Une demi-journée.

## Risques

Un test qui cherche un titre par son niveau change avec le passage à
`RegionTitle`.