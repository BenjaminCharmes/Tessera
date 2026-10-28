---
id: ticket-627
title: "The Bureau wall keeps three windows and gains a bookcase, behind a narrower whiteboard"
type: fix
status: done
pr_number: 707
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-10-28
---

# ticket-627 — Trois fenêtres et une bibliothèque au mur de chaque pièce

## Objectif
Faire de la place au mur d'une pièce pour la bibliothèque où les rédacteurs se
tiendront (ticket-624), sans perdre de fenêtre.

## Contexte
Le 28/10, la bibliothèque devait remplacer la fenêtre du milieu. Benjamin
préfère garder trois fenêtres pour la taille de la pièce, quitte à resserrer ce
qui est en place et à rétrécir le tableau blanc.

## Solution proposée
- Le tableau blanc passe de 132 à 96 px de large (grille 32 × 14). Il garde six
  lignes par colonne et deux colonnes au plus.
- Les deux premières fenêtres se resserrent derrière lui (`FENETRES_X`).
- La bibliothèque, mobilier toujours dessiné et sans voyant, se pose au sol entre
  la deuxième fenêtre et le ficus. Son abscisse est `BIBLIOTHEQUE_X` dans
  `lib/bureau/activites.ts`, pour que le ticket-624 y ancre les rédacteurs.

## Critères d'acceptation
- [x] `FENETRES_X` compte toujours trois fenêtres
- [x] `TableauBlanc.tsx` dessine une grille de 32 × 14
- [x] `FondDeLaPiece.tsx` pose `Bibliotheque` à `BIBLIOTHEQUE_X`
- [x] Captures à 1920 et 1536 relues : aucun objet du mur n'en chevauche un autre

## Ce que ça ne fait pas
- Ne dessine pas les rédacteurs : c'est le ticket-624.
