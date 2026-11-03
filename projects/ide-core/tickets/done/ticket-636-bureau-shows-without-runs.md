---
id: ticket-636
title: "The Bureau stays on screen when no run is open"
type: fix
status: done
pr_number: null
priority: low
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-10-28
---

# ticket-636 — Le Bureau reste affiché sans run

## Objectif
Garder le Bureau à l'écran quand aucun run n'est ouvert.

## Contexte
Le 28/10, sans run, un message plein écran remplaçait tout le Bureau. Les salles
du haut, la colonne « À toi » et l'employé de la semaine disparaissaient, alors
qu'ils ne dépendent pas d'un run.

## Solution proposée
- `BureauConnecte` n'affiche le message plein écran que si le canal d'observation
  est coupé, là où il dit quelque chose d'utile.
- Sans run, `BureauView` met une ligne « Aucun run en cours » à la place des pièces.

## Critères d'acceptation
- [x] Un test vérifie que, sans run, la Supervision montre la salle de pause et la ligne « Aucun run en cours »

## Ce que ça ne fait pas
- Ne change pas la Liste, qui garde son message.
