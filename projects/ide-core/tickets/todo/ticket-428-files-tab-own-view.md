---
id: ticket-428
title: "The Files tab shows the open file, a search and recent files when none is open, or the ticket's diff, instead of the tickets list"
type: feat
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: ["ticket-425"]
estimated_days: 1
created: 2026-10-14
---

# ticket-428 — Onglet Fichiers : sa propre vue

## Objectif

Que l'onglet Fichiers montre au centre l'éditeur ou le diff du ticket, et,
sans fichier ouvert, de quoi en ouvrir un — au lieu de la liste des
tickets.

## Contexte

Même cause que le ticket-427 : `components/CenterView.tsx` retombe sur
`vueDuCentre`, qui affiche la liste des tickets quand aucun fichier n'est
ouvert. Maquette validée :
`projects/ide-core/design/maquette/Fichiers.dc.html`.

Existant : `Editor` (fichier ouvert), `DiffView` (diff d'un ticket,
`projectId` + `ticketId`), la colonne `FileTree`, et
`GET /api/v1/projects/{id}/tickets/{ticket_id}/diff`.

## Solution proposée

- `CenterView` : `panel === "files"` rend `FichiersView`
  (`components/FichiersView/`).
- En-tête : titre « Fichiers » et un sélecteur « Éditeur » (défaut) /
  « Diff du ticket ».
- **Éditeur**, fichier ouvert : `Editor`, comme aujourd'hui.
- **Éditeur**, aucun fichier ouvert (maquette) : « Aucun fichier ouvert »,
  un champ « Rechercher un fichier… » qui filtre les fichiers du projet par
  nom (liste déjà chargée par `FileTree`, ou même source) et ouvre celui
  qu'on choisit ; « Touchés par le dernier run — ticket-N » (fichiers du
  diff du ticket sélectionné, ou du dernier ticket terminé, avec lignes
  ajoutées / retirées) ; « Ouverts récemment » (les 5 derniers fichiers
  ouverts dans ce projet, mémorisés par projet dans le stockage local).
- **Diff du ticket** : `DiffView` du ticket sélectionné ; sans ticket
  sélectionné, « Sélectionne un ticket pour voir son diff ».
- Le raccourci Ctrl+P met le focus sur le champ de recherche quand l'onglet
  Fichiers est actif (et seulement lui).

## Critères d'acceptation

- [ ] Un test de `CenterView` vérifie que l'onglet Fichiers rend
      `FichiersView` et non la liste des tickets
- [ ] Un test vérifie que, sans fichier ouvert, la vue affiche la recherche,
      les fichiers touchés et les fichiers récents
- [ ] Un test vérifie que choisir un résultat de recherche ouvre ce fichier
- [ ] Un test vérifie que les fichiers récents sont mémorisés par projet et
      limités à 5
- [ ] Un test vérifie que « Diff du ticket » rend `DiffView` du ticket
      sélectionné, et le message d'invitation sans ticket

## Dépendances

ticket-425.
