---
id: ticket-281
title: "A finished run can be reopened in the run view from the run history"
type: feat
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: ["ticket-280", "ticket-279"]
estimated_days: 1
created: 2026-10-01
---

# ticket-281 — Un run terminé se rouvre depuis l'historique

## Objectif

Qu'on puisse revoir la vue « Agents » d'un run une fois qu'il a quitté la
Supervision : étapes, cartes codeur / sécurité / reviewer / validateur,
résumé de fin.

## Contexte

La carte d'un run disparaît de la Supervision à sa fermeture ou au premier
rechargement : l'instantané de la WebSocket ne contient que les runs vivants
(`routers/observation.py:84`). Le ticket-280 rend les événements d'un run
terminé ; la vue sait déjà se construire depuis une suite d'événements
(`streamState.applyEvent`).

## Solution proposée

- Une ligne de `StatsView/RecentRuns` devient cliquable et ouvre la vue du
  run, construite en rejouant ses événements dans `applyEvent`.
- La vue rouverte est en lecture seule : ni arrêt, ni message aux agents, ni
  chrono qui tourne.
- Un bouton la referme et ramène à l'historique.

## Critères d'acceptation

- [ ] Un test vérifie qu'un clic sur une ligne de `RecentRuns` appelle
      l'endpoint du ticket-280 avec l'identifiant de cette ligne
- [ ] Un test vérifie que la vue rouverte affiche les cartes et le verdict
      issus des événements reçus
- [ ] Un test vérifie que la vue rouverte n'affiche ni bouton d'arrêt ni champ
      de message
- [ ] Un test vérifie qu'une erreur de l'endpoint affiche un message au lieu
      d'une vue vide

## Dépendances

ticket-280 (l'endpoint), ticket-279 (une suite d'événements terminée se rend
comme terminée).

## Estimation

1 jour.

## Risques

Aucun appel d'agent : le coût est une requête SQLite par ouverture.
