---
id: ticket-637
title: "The shared rooms write who is inside in their header, not on the floor behind the decor"
type: fix
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-10-28
---

# ticket-637 — Le texte des salles du haut passe dans leur en-tête

## Objectif
Que le texte d'une salle du haut se lise, au lieu de passer derrière le décor.

## Contexte
Le 28/10, un agent devant le directeur avait son « ide-core · Codeur » écrit au
sol, entre le mobilier et la bibliothèque, qui le recouvrait. Les quatre salles
posaient ainsi leurs occupants dans le sol (`Salle.tsx`).

## Solution proposée
- `Salle` reçoit `textes` : une ligne par occupant, écrite dans l'en-tête à la
  place du message de salle vide.
- Le sol ne garde que les personnages (directeur, RH) ; la pause et la réunion
  n'en ont pas.

## Critères d'acceptation
- [x] Un test vérifie que le nom du projet d'un agent devant le directeur est hors du sol, que l'agent est dessiné au sol, et que « Aucune question en attente » disparaît

## Ce que ça ne fait pas
- Ne dessine pas de résolveur dans la salle de réunion : c'est le ticket-624.
