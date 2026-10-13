---
agent: codeur
created: 2026-10-13
depends_on: []
estimated_days: 0.5
id: ticket-412
pr_number: null
priority: medium
status: done
title: Each project card in the Projects view can launch the queue of its to-do tickets,
  after a confirmation
type: feat
---

# ticket-412 — Lancer la file d'un projet depuis sa carte

## Objectif

Lancer le pipeline sur les tickets à faire de plusieurs projets d'affilée,
depuis la vue Projets, sans ouvrir chacun d'eux.

## Contexte

Demandé par Benjamin le 2026-10-13, avec le ticket-411. Aujourd'hui, une
file se compose ticket par ticket dans la colonne du projet actif
(`QueueBar`, `useCockpit`), puis part par `POST /api/v1/orchestrator/run`
en mode `queue`. La carte connaît déjà `tickets.todo` et `run_actif`
(ticket-398).

## Solution proposée

- Sur `ProjetCarte` (`components/ProjetsView/ProjetCarte.tsx`), quand
  `tickets.todo > 0` : un bouton « File (N) ». Désactivé, avec une
  infobulle « Un run est en cours », quand `run_actif` est vrai.
- Premier clic : la carte demande confirmation sur place (« Lancer N
  tickets ? » avec « Lancer » / « Annuler »), sans fenêtre modale. Le clic
  arrête la propagation : la carte n'est pas sélectionnée.
- « Lancer » : lit les tickets du projet (`api.tickets.list` ou
  équivalent), garde ceux au statut `todo`, triés par id, et appelle
  `POST /orchestrator/run` `{ "project_id", "mode": "queue",
  "ticket_ids" }` ; puis relecture de la vue d'ensemble, où le point
  « run en cours » apparaît.
- Échec (409 si un run tourne déjà, autre erreur) : message court en `red`.

## Critères d'acceptation

- [ ] Un test vérifie que le bouton n'apparaît pas quand `tickets.todo` vaut 0
- [ ] Un test vérifie que le bouton est désactivé quand `run_actif` est vrai
- [ ] Un test vérifie qu'un premier clic affiche la confirmation sans rien
      lancer et sans appeler `onSelect`
- [ ] Un test vérifie que « Lancer » envoie `mode: "queue"` avec les seuls
      tickets `todo`, triés par id
- [ ] Un test vérifie qu'une réponse 409 affiche un message d'erreur

## Dépendances

Aucune.

## Ce que ça ne fait pas

- Pas de choix des tickets depuis la carte : c'est tout le « à faire », dans
  l'ordre des ids. Pour choisir, la colonne du projet reste là.