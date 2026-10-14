---
id: ticket-426
title: "The navigation rail is grouped into Pilotage, Projet and Outils, as in the validated mockup"
type: feat
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-14
---

# ticket-426 — Navigation regroupée : Pilotage, Projet, Outils

## Objectif

Que la barre de navigation se lise par usage : ce qui pilote tous les
projets, ce qui concerne le projet actif, les outils.

## Contexte

Maquette validée par Benjamin le 2026-10-14 :
`projects/ide-core/design/maquette/Fichiers.dc.html` (la barre de gauche est
la même sur les trois écrans). `components/Sidebar/NavRail.tsx` liste
aujourd'hui neuf destinations à plat (Projets, En cours, Tickets, Fichiers,
Historique, Agents, Supervision, Statistiques, Chat).

## Solution proposée

- Trois groupes, dans cet ordre, chacun précédé d'un intitulé discret en
  petites capitales et séparés par un filet :
  - **Pilotage** : Projets, En cours, Supervision ;
  - **Projet** : Tickets, Fichiers, Historique ;
  - **Outils** : Agents, Statistiques, Chat.
- Les pastilles existantes (En cours, Supervision) et l'état actif (fond et
  contour violets, `aria-current="page"`) sont conservés.
- Chaque groupe est une liste à part, nommée (`aria-label`), pour les
  lecteurs d'écran.

## Critères d'acceptation

- [ ] Un test de `NavRail` vérifie l'ordre des neuf destinations : Projets,
      En cours, Supervision, Tickets, Fichiers, Historique, Agents,
      Statistiques, Chat
- [ ] Un test vérifie la présence des intitulés « Pilotage », « Projet » et
      « Outils », chacun avant les destinations de son groupe
- [ ] Les tests existants de `NavRail` (pastilles, état actif) restent verts

## Dépendances

Aucune.
