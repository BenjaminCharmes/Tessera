---
id: ticket-223
title: "Le chat a sa propre vue, la colonne de droite disparaît"
type: feat
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-29
---

# ticket-223 — Le chat a sa propre vue

## Objectif

L'espace central gagne la largeur de la colonne de droite. Le chat devient une vue de la barre de navigation, comme Supervision ou Tickets.

## Contexte

La colonne de droite de `App.tsx` a deux onglets, « Agents » et « Chat ». Dans la vue Supervision, l'onglet Agents répète le panneau qui s'affiche déjà au centre (`SupervisionView` importe `AgentPanel`). Sur le Kanban, il fait doublon avec la Supervision, qui suit déjà tous les runs de tous les projets (ADR-041). Le chat, lui, n'a aucune raison de partager une colonne étroite avec un run.

## Solution proposée

`NavRail` gagne une entrée « Chat », qui affiche `ChatPanel` au centre. La colonne de droite et son état persistant (`onglet-droit`) sont supprimés, et le suivi d'un run passe par la vue Supervision. Frontend uniquement.

## Critères d'acceptation

- [ ] Un test Vitest : `NavRail` propose une entrée « Chat »
- [ ] Un test Vitest : choisir « Chat » affiche `ChatPanel` dans la zone centrale
- [ ] Un test Vitest : `App` ne rend plus d'onglets « Agents » / « Chat » en colonne de droite
- [ ] La vue Supervision affiche toujours le panneau Agents du run (test existant vert, ou test ajouté)
- [ ] Aucune lecture de la clé `onglet-droit` ne subsiste dans `App.tsx`

## Dépendances

Aucune.
