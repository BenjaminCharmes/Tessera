---
agent: codeur
created: 2026-11-12
depends_on: []
estimated_days: 0.2
id: ticket-955
pr_number: null
priority: medium
status: done
title: "The project card footer stays inside the card, whatever its counters and buttons"
type: fix
---

# ticket-955 — Le pied d'une carte projet reste dans la carte, quels que soient ses compteurs et ses boutons

## Objectif

Qu'aucun compteur ni bouton ne sorte d'une carte de la vue Projets.

## Contexte

Le 12/11, Benjamin a relevé sur la carte Repo Health « À faire 13 Faits 27 »
cassé mot à mot et sorti par le bas de la carte, sur Serpent et Homelab
aussi. Les compteurs partageaient une rangée de hauteur fixe (`h-7`) avec deux
ou trois boutons (ticket-633) ; sans place, ils se repliaient mot par mot. La
capture de vérification a montré un second débordement : « Ajouter à la file
(1) » et deux boutons sortaient par la gauche de la carte Homelab.

## Solution

- Les compteurs passent sur la ligne des dates, à droite, sans retour à la
  ligne ; les dates se replient à leur place si besoin.
- La rangée des boutons garde sa hauteur minimale et laisse les boutons passer
  à la ligne au lieu de déborder.

## Critères d'acceptation

- [x] Les compteurs sont sur la ligne des dates, `whitespace-nowrap`
      (test vitest).
- [x] La rangée des boutons est `min-h-7`, ses boutons en `flex-wrap`
      (test vitest).
- [x] Captures 1920 et 1536 sur les vraies données : aucun compteur ni bouton
      hors de sa carte.

## Ce que ça ne fait pas

- Ne raccourcit aucun libellé de bouton.
