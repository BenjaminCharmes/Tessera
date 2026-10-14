---
id: ticket-441
title: "Settings move behind a button at the bottom of the rail, and the column header keeps only the project, its run state and its actions"
type: feat
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-14
---

# ticket-441 — Réglages dans le rail, en-tête de colonne allégé

## Objectif

Que l'en-tête de la colonne ne montre que ce qui concerne le projet actif.

## Contexte

Audit du 2026-10-14 : sous le nom du projet, chaque onglet répète la case
« Notifications » avec « bloquées par le navigateur : à autoriser dans ses
réglages de site », le panneau « Pipeline » replié et la phrase
« « ide-core » fait tourner l'IDE. » (`components/Sidebar/` :
`ReglageNotifications`, `PanneauxDuProjet`). Ces réglages sont globaux, pas
propres au projet. Maquette validée :
`projects/ide-core/design/maquette/Cadre.dc.html`.

## Solution proposée

- Un bouton « Réglages » (icône engrenage, `aria-label`) en bas du rail de
  navigation ouvre un panneau qui regroupe le réglage des notifications et
  les plafonds de dépense (aujourd'hui affichés dans la colonne de
  Statistiques, qui les garde aussi).
- L'en-tête de colonne garde : le sélecteur de projet, une pastille
  « run en cours » quand un run tourne sur ce projet, puis la ligne
  d'actions (Services, VSCode, Git, Signaler).
- « ce projet fait tourner l'IDE » devient l'infobulle du nom de projet.
- Le panneau « Pipeline » du projet reste accessible depuis l'onglet Agents
  ou Tickets (là où il sert), plus depuis l'en-tête.

## Critères d'acceptation

- [ ] Un test de `NavRail` vérifie la présence du bouton « Réglages » et que
      son clic ouvre le panneau contenant le réglage des notifications
- [ ] Un test vérifie que l'en-tête de colonne ne contient plus le texte
      « bloquées par le navigateur »
- [ ] Un test vérifie que la pastille « run en cours » s'affiche quand un run
      tourne sur le projet actif, et seulement alors
- [ ] Un test vérifie que « fait tourner l'IDE » est porté par l'attribut
      `title` du nom de projet

## Dépendances

Aucune.
