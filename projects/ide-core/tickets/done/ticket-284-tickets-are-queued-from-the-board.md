---
agent: codeur
created: 2026-10-01
depends_on: []
estimated_days: 0.5
id: ticket-284
pr_number: 181
priority: medium
status: done
title: Tickets can be added to the queue from the board view
type: feat
---

# ticket-284 — La file se compose depuis la Vue Tableau

## Objectif

Que la Vue Tableau permette d'ajouter des tickets à la file et de la lancer,
comme la liste de la sidebar.

## Contexte

`TicketCard` porte déjà le bouton « Ajouter à la file » / « Retirer de la
file » (`Sidebar/TicketCard.tsx:263-279`), rendu seulement si `onToggleQueue`
est passé. `TicketList` le passe (`:268-269`) et monte `QueueBar` (« N tickets
en file », « Lancer la file », « Vider »). `KanbanView/KanbanColumn.tsx:94-104`
ne passe ni `onToggleQueue` ni `dansLaFile`, et la Vue Tableau n'a pas de
`QueueBar` : on n'y lance qu'un ticket à la fois.

## Solution proposée

- `KanbanView` reçoit la sélection de file de `useCockpit` et la passe à
  chaque `KanbanColumn`, qui la transmet aux cartes.
- La Vue Tableau monte `QueueBar` au-dessus des colonnes, sur la même
  sélection que la sidebar : un ajout fait dans l'une se voit dans l'autre.

## Critères d'acceptation

- [ ] Un test de `KanbanColumn` vérifie qu'une carte `todo` affiche le bouton
      « Ajouter à la file » et qu'un clic appelle `onToggleQueue` avec son id
- [ ] Un test de `KanbanView` vérifie que `QueueBar` est rendu quand la
      sélection contient au moins un ticket
- [ ] Un test vérifie qu'un ticket ajouté depuis la Vue Tableau figure dans la
      sélection lue par la sidebar

## Dépendances

Aucune.

## Estimation

0,5 jour.

## Risques

Aucun : le mécanisme existe, seul le câblage manque.