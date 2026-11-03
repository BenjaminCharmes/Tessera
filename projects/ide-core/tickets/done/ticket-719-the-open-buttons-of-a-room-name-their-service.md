---
id: ticket-719
title: "The open buttons of a server room name their service"
type: fix
status: done
pr_number: null
priority: low
agent: codeur
depends_on: []
estimated_days: 0.1
created: 2026-10-30
---

# ticket-719 — Les boutons « Ouvrir » d'une salle nomment leur service

## Objectif
Sur la plaque d'une salle, chaque bouton dit quel service il ouvre.

## Contexte
Retour de Benjamin le 30/10 sur la salle livrée par le ticket-710 : « Ouvrir :5196 »
ne disait pas s'il s'agissait du frontend ou du backend.

## Fait
Le bouton devient « Ouvrir <service> :<port> », le nom venant de l'app de
l'inventaire qui écoute ce port. Retouche à la main.

## Critères d'acceptation
- [x] `SallesDesServeurs.test.tsx` : deux services donnent « Ouvrir backend :8026 » et « Ouvrir frontend :5196 », chacun vers son port
