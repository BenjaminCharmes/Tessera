---
id: ticket-216
title: "Le compte rendu du codeur reste visible après son tour"
type: fix
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-28
---

# ticket-216 — Le compte rendu du codeur reste visible

## Objectif

Le bloc CODEUR du panneau Agents montre ce que le codeur a fait, même quand le panneau s'ouvre ou se reconnecte après la fin de son tour.

## Contexte

`AgentBlock` n'affiche pour le codeur que les tokens reçus en direct (`agent_token`). ADR-041 jette ce texte en premier quand un client décroche, et il n'est pas rejoué à la reconnexion. Un panneau ouvert après coup montre donc un bloc « terminé » vide. Pourtant, le compte rendu complet est dans l'événement `agent_done` (3 358 caractères sur le run du ticket-214). Le reviewer ne pose pas ce problème : son bloc lit `reviewContent`, qui vient de `agent_done`.

## Solution proposée

Quand le codeur est terminé et que les tokens reçus sont vides, ou plus courts que le contenu de `agent_done`, le bloc affiche ce contenu, replié par défaut comme le détail du reviewer.

## Critères d'acceptation

- [ ] Un test Vitest : bloc codeur terminé, sans tokens, avec un contenu `agent_done` → le texte du compte rendu est rendu
- [ ] Un test Vitest : tokens reçus en direct → ils restent affichés comme aujourd'hui (non-régression)
- [ ] Le compte rendu est replié par défaut, et un clic le déplie
- [ ] `npm run test` passe

## Dépendances

Aucune.

## Estimation

0,5 jour.

## Risques

Aucun sur le backend : l'événement existe déjà.
