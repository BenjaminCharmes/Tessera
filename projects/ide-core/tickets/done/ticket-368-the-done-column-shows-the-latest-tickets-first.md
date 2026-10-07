---
agent: codeur
created: 2026-10-07
depends_on: []
estimated_days: 0.5
id: ticket-368
pr_number: 308
priority: medium
status: done
title: The kanban's done and cancelled columns show the 30 latest tickets, the rest
  on demand
type: feat
---

# ticket-368 — Les colonnes terminées du kanban montrent les 30 derniers tickets

## Objectif

Que le kanban reste léger quand le projet accumule des tickets terminés :
seules les cartes récentes sont rendues, le reste à la demande.

## Contexte

`frontend/src/components/KanbanView/KanbanColumn.tsx` rend une `TicketCard`
par ticket de la colonne. Le 2026-10-07, la colonne DONE d'ide-core en rend
350, et ce nombre ne fait que croître : autant de composants montés, de
nœuds DOM et de rendus à chaque mise à jour, pour des tickets qu'on ne
consulte presque jamais. Les colonnes actives (todo, in-progress, in-review,
blocked) restent courtes et ne sont pas concernées.

## Solution proposée

Dans les colonnes `done` et `cancelled` seulement, rendre les 30 tickets au
numéro le plus élevé, puis un bouton « Afficher les N autres » qui rend la
totalité. Le compteur de la colonne garde le total réel. La recherche et les
filtres de la vue s'appliquent avant la limite : un ticket ancien recherché
apparaît.

## Critères d'acceptation

- [ ] Un test de `frontend/src/components/KanbanView/KanbanColumn.test.tsx` rend une colonne `done` de 50 tickets et vérifie que 30 cartes sont rendues, celles des 30 numéros les plus élevés
- [ ] Un test de `frontend/src/components/KanbanView/KanbanColumn.test.tsx` vérifie que le bouton « Afficher les 20 autres » rend les 50 cartes après un clic
- [ ] Un test de `frontend/src/components/KanbanView/KanbanColumn.test.tsx` vérifie qu'une colonne `todo` de 50 tickets rend ses 50 cartes
- [ ] Un test de `frontend/src/components/KanbanView/KanbanColumn.test.tsx` vérifie que le compteur de la colonne `done` affiche 50 quand 30 cartes sont rendues

## Dépendances

Aucune.

## Estimation

0,5 jour.

## Risques

Un ticket terminé ancien n'est plus visible d'un coup d'œil ; la recherche et
le bouton le retrouvent.

## Ce que ça ne fait pas

- Ne change pas la liste de la barre latérale, où la section DONE est déjà
  repliée par défaut.
- Pas de virtualisation de liste.