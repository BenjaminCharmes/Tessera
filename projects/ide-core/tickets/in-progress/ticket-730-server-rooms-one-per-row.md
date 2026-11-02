---
id: ticket-730
title: "Server rooms: one per row, desks on a single floor row"
type: fix
status: in-progress
pr_number: null
priority: high
agent: codeur
depends_on: [ticket-729]
estimated_days: 1
created: 2026-11-02
---

# ticket-730 — Salles serveur : une par ligne, les postes au sol sur une seule ligne

## Objectif
Que chaque salle de « En cours » garde une hauteur fixe et que ses postes d'agents restent
posés au sol, quel que soit leur nombre.

## Contexte
Benjamin, le 02/11, avec Vigie (3 agents) et Affût (5) à l'écran : pas la place sur une
ligne, des bureaux qui « volent », des salles de hauteurs différentes. Les agents étaient
posés entre le mobilier du mur, dans une rangée qui passait à la ligne ; deux salles par
ligne à partir de 1280 px.

## Solution proposée
- Une salle par ligne, à toutes les largeurs.
- Deux plans : le mur (baies, clim, VMC, extincteur, porte), puis une rangée de postes au
  sol, une seule ligne ; sa capacité se mesure (`ResizeObserver`) et, au-delà, le dernier
  poste devient un badge « +N agents » ; les agents au travail passent devant.
- Sans agent : trois postes vides, écran éteint, sans personne (`PosteVide`) — du
  mobilier, ni animation ni voyant (ADR-058).

## Critères d'acceptation
- [ ] `SallesDesServeurs.tsx` n'a plus de colonne double ; un test le vérifie
- [ ] `rangee.ts` calcule la capacité et le badge « +N », agents au travail d'abord ; testé
- [ ] Une salle sans agent montre trois `poste-vide` et aucun agent ; un test le vérifie
- [ ] Benjamin a validé le rendu sur 5176 (captures 1920 et 1536)
