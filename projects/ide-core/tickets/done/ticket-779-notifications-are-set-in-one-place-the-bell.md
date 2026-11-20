---
id: ticket-779
title: "Notifications are set in one place, the bell, and the sun-shaped settings button goes"
type: fix
status: done
pr_number: null
priority: low
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-04
---

# ticket-779 — Les notifications se règlent à un seul endroit, la cloche

## Objectif

Le pied du rail ne propose plus deux endroits pour régler les notifications, ni un bouton qui
ressemble à un sélecteur de thème.

## Contexte

Relevé par Benjamin le 04/11. Le bouton « Réglages » (`BoutonReglages`, ticket-441) portait une
icône `IconSettings` dessinée comme un soleil, alors que Tessera n'a pas de mode clair. Son
panneau tenait l'interrupteur global des notifications, déjà voisin de la cloche et de son onglet
« Réglages » (ticket-554), et les plafonds de dépense en lecture seule, que la colonne des
Statistiques affiche déjà.

## Solution

Faite à la main.
- L'interrupteur global (`ReglageNotifications`) passe en tête de l'onglet « Réglages » de la
  cloche (`Cloche.tsx`).
- `BoutonReglages.tsx` est supprimé ; `PlafondsDeDepense` reste dans la colonne des Statistiques.

## Critères d'acceptation

- [x] `NavRail.test.tsx` vérifie qu'il n'y a plus de bouton « Réglages » dans le rail
- [x] `NavRail.test.tsx` vérifie que l'interrupteur global est en tête de l'onglet « Réglages »
      de la cloche et qu'un changement y est relayé

## Ce que ça ne fait pas

Pas de réglages globaux modifiables : c'est l'objet d'une conception à part (plafonds, tests en
parallèle, maintien éveillé…). Un bouton reviendra, avec un vrai engrenage, quand ils existeront.
