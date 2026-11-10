---
agent: codeur
created: 2026-11-10
depends_on: []
estimated_days: 0.25
id: ticket-909
pr_number: null
priority: low
status: done
title: BureauView tests pay the cold render once, outside any test
type: test
---

# ticket-909 — Les tests de BureauView paient le premier rendu une fois, hors de tout test

## Objectif

Qu'un run ne se bloque plus parce que la machine est chargée au moment où le
premier test de `BureauView` fait son premier rendu.

## Contexte

Le 10/11, le ticket-902, qui ne touche aucun fichier du Bureau, a été bloqué
au tour 3 : `BureauView.test.tsx > renders ten rooms under 2250 SVG nodes` a
dépassé les 15 s de `testTimeout`. Un run Kadoomi tournait en parallèle. Relancé
seul, le même fichier passe en 1,3 s, et ce test en 0,5 s.

C'est toujours le **premier** test du fichier qui paie le rendu à froid : dix
pièces, environ 2 000 nœuds SVG, et le premier passage de jsdom et de React sur
tous les sprites. Sous charge, ce coût est multiplié et déborde du délai, alors
que le test ne mesure aucun temps : il compte des nœuds.

## Solution proposée

- Un `beforeAll` de `BureauView.test.tsx` rend `<DixPieces />` une fois puis le
  démonte, avec les mêmes doubles d'API que le `beforeEach`, et un délai de
  60 000 ms passé en dernier argument du `beforeAll`. Le coût à froid se paie
  là, une fois, hors de tout test.
- Les tests gardent le délai global de 15 s : aucun test ne reçoit un délai
  plus long.

## Critères d'acceptation

- [ ] `frontend/src/components/BureauView/BureauView.test.tsx` contient un
      `beforeAll` qui rend `DixPieces` puis l'appelle `unmount`, avec `60_000`
      (ou `60000`) en dernier argument.
- [ ] Aucun `it(...)` de `BureauView.test.tsx` ne reçoit de délai en
      argument.
- [ ] Le diff ne modifie que `frontend/src/components/BureauView/BureauView.test.tsx`
      (hors suivi du ticket et `memory/pipeline-log.md`) : ni `vite.config.ts`,
      ni aucun autre fichier de configuration des tests.

## Ce que ça ne fait pas

- Ne relève pas `testTimeout` global : il garde sa valeur.
- Ne traite pas d'autre fichier : un autre test lent sous charge aura son
  ticket, avec sa mesure.

## Dépendances

Aucune.

## Estimation

Un quart de journée.

## Risques

- Le `beforeAll` doit poser ses doubles d'API lui-même : ceux du `beforeEach`
  ne sont pas encore en place quand il s'exécute.