---
id: ticket-634
title: "The whiteboard keeps a margin under its sixth row"
type: fix
status: done
pr_number: null
priority: low
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-10-28
---

# ticket-634 — Une marge sous la sixième ligne du tableau

## Objectif
Que la dernière case du tableau blanc reste dans le tableau.

## Contexte
Le 28/10, avec six critères, la sixième case touchait le cadre : la grille de
26 lignes n'avait pas de marge en bas, alors qu'elle en a une en haut.

## Solution proposée
La grille passe à 44 × 27 (88 × 54 px) : une ligne de marge en bas, comme en haut.

## Critères d'acceptation
- [x] Un test de `TableauBlanc` vérifie qu'avec six critères la marge sous la dernière case égale celle au-dessus de la première

## Ce que ça ne fait pas
- Ne change ni le nombre de lignes par colonne ni la largeur.
