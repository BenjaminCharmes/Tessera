---
agent: codeur
created: 2026-09-30
depends_on: []
estimated_days: 0.5
id: ticket-271
pr_number: null
priority: medium
status: done
title: Switching project keeps the active tab
type: feat
---

# ticket-271 — Changer de projet garde l'onglet actif

## Objectif

Qu'un changement de projet par le sélecteur laisse l'utilisateur sur l'onglet
où il était (Statistiques, Chat, Fichiers…), au lieu de le renvoyer sur
Tickets.

## Contexte

Demande utilisateur du 2026-09-30. `handleSelectProject`
(`frontend/src/hooks/useCockpit.ts`) appelle `setPanel("tickets")` à chaque
changement de projet, quelle que soit son origine : le sélecteur de projet
(`SelecteurDeProjet`) comme la liste de l'onglet Projets.

Depuis la liste de l'onglet **Projets**, ouvrir les tickets reste attendu :
c'est ce qu'on vient y chercher. Depuis le sélecteur, non.

## Solution proposée

- `handleSelectProject` ne change d'onglet que si l'onglet actif est
  `projects` ; il bascule alors sur `tickets`. Sur tout autre onglet, l'onglet
  reste.
- Le reste de ce qu'il réinitialise (fichier ouvert, flux du run, vue
  tableau) ne change pas.

## Critères d'acceptation

- [ ] Un test montre qu'avec l'onglet `usage` actif, choisir un autre projet
      laisse l'onglet `usage` actif.
- [ ] Un test montre qu'avec l'onglet `chat` actif, choisir un autre projet
      laisse l'onglet `chat` actif.
- [ ] Un test montre qu'avec l'onglet `projects` actif, choisir un projet
      bascule sur l'onglet `tickets`.

## Dépendances

Aucune.

## Estimation

Une demi-journée. Frontend uniquement.

## Risques

Le chat retient sa conversation par projet (ticket-250) : vérifier qu'en
restant sur l'onglet Chat, le changement de projet affiche bien la
conversation du nouveau projet.