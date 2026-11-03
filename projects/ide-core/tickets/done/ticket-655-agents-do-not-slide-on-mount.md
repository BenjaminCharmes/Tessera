---
id: ticket-655
title: "Bureau agents no longer slide in from the left when the view is shown again"
type: fix
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-10-28
---

# ticket-655 — Les agents ne glissent plus depuis la gauche au retour sur la vue

## Objectif
Qu'au retour sur le Bureau, chaque agent soit déjà à sa place.

## Contexte
Le 28/10, à chaque changement d'onglet, tous les agents debout glissaient depuis
la gauche jusqu'à leur place. `SolEtire` lit la largeur du sol au montage
(`clientWidth`) : cette lecture calcule le style des agents à l'étirement 1, et le
vrai étirement qui suit déclenche la transition de marche de 1,8 s (`.marche`).

Mesuré avec Playwright après un changement d'onglet : avant le correctif, les
agents étaient à 237, 399, 561 px à 150 ms, puis à 265, 477, 689 px à 1650 ms.
Après, ils sont à leur place dès 150 ms.

## Solution proposée
`SolEtire` ne fournit `MarcheActive` qu'après une image peinte à la bonne place
(`requestAnimationFrame`). `AgentsDeLaPiece` ne pose la classe `marche` qu'à
partir de là.

## Critères d'acceptation
- [x] Un test de `SolEtire` vérifie que la marche est coupée au premier rendu, puis active à l'image suivante

## Ce que ça ne fait pas
- Ne change pas la marche d'un agent qui change d'activité sur une vue déjà affichée.
