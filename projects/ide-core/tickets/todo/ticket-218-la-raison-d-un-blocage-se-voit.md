---
id: ticket-218
title: "La raison d'un run bloqué se voit sur la carte et dans la Supervision"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-28
---

# ticket-218 — La raison d'un blocage se voit

## Objectif

Quand un run finit en `blocked`, l'utilisateur lit pourquoi sans ouvrir la base : sur la carte du ticket et dans le panneau « Ce que ce ticket a produit ».

## Contexte

Le run du ticket-213 s'est arrêté sur « Reached maximum number of turns (30) ». La cause était dans `run_closed.arret` et dans l'événement `error`, mais la vue Supervision affichait « Aucun run en cours », la carte affichait seulement `blocked`, et le panneau du ticket affichait « blocked · 1 tour(s) ». L'utilisateur ne pouvait pas savoir si c'était la revue, la sécurité, une panne ou une limite.

## Solution proposée

`GET …/tickets/{id}/activity` expose l'`arret` et la `reason` du dernier run. Le panneau les affiche sous le statut, et la carte en porte une version courte en infobulle.

## Critères d'acceptation

- [ ] Un test : un run clos avec `arret` renseigné → l'activité du ticket expose cet `arret`
- [ ] Un test Vitest : une activité `blocked` avec un `arret` → le texte de l'arrêt est rendu dans le panneau
- [ ] Un test Vitest : une carte `blocked` porte l'arrêt dans son attribut `title`

## Dépendances

Aucune.

## Estimation

1 jour.
