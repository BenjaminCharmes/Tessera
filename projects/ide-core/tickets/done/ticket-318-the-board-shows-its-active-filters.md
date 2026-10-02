---
agent: codeur
created: 2026-10-02
depends_on: []
estimated_days: 0.5
id: ticket-318
pr_number: null
priority: high
status: done
title: The board shows when remembered filters hide tickets, and clears them in one
  click
type: fix
---

# ticket-318 — Le tableau dit quand des filtres mémorisés cachent des tickets

## Objectif

Qu'on ne puisse plus croire que des tickets ont disparu alors qu'un filtre
les cache.

## Contexte

Le 2026-10-02, la Vue Tableau d'ide-core n'affichait que 4 tickets `done` sur
297. Le backend les rendait tous, et un navigateur neuf les affichait tous
(Playwright : `DONE (297)`). Dans le navigateur de l'utilisateur, un filtre
posé plus tôt restait actif.

- Les filtres sont mémorisés par projet dans `localStorage`
  (`useFiltresTickets` via `useEtatPersistant`, clé `tessera.ui.*`) : ils
  survivent aux rechargements et aux redémarrages.
- La Vue Tableau les applique (`useCockpit.ts:211` et `:428`, `byStatus`
  filtré).
- Mais la barre de filtres et son compteur « X sur Y »
  (`Sidebar/BarreDeFiltres.tsx:105`) n'existent que dans le panneau Tickets
  de la barre latérale. Si ce panneau n'est pas ouvert, rien n'indique qu'un
  filtre est actif.

## Solution proposée

- Quand des filtres sont actifs, la Vue Tableau affiche au-dessus des
  colonnes une ligne qui les nomme et donne le compte (« Filtres : type
  design · 4 tickets sur 297 »), avec un bouton « Effacer les filtres ».
- Le bouton remet les filtres du projet à leur valeur par défaut, et la
  mémoire aussi.

## Critères d'acceptation

- [ ] Un test de `KanbanView` vérifie qu'avec un filtre actif, la ligne
      « N tickets sur M » s'affiche avec les bons nombres
- [ ] Un test vérifie que sans filtre actif, cette ligne n'est pas rendue
- [ ] Un test vérifie qu'un clic sur « Effacer les filtres » réaffiche tous
      les tickets, et que les filtres mémorisés du projet sont remis à zéro
- [ ] Un test vérifie que la ligne nomme chaque filtre actif (texte, type,
      priorité, agent)

## Dépendances

Aucune.

## Risques

Aucun : le filtrage existe, seule sa visibilité change.