---
id: ticket-728
title: "UI touch-ups from the 2 November review"
type: fix
status: done
pr_number: 815
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-02
---

# ticket-728 — Retouches UI relevées le 02/11

## Objectif

Corriger, en un lot, les défauts d'interface que Benjamin relève en direct le 02/11.
Fait à la main (petites retouches), servi sur un Vite à part pour sa revue.

## Contexte

Relevés au fil de la matinée :

1. **« En lancement » ne se lève pas** : un projet lancé depuis « En cours » reste
   « En lancement », et sa salle n'apparaît qu'après actualisation. Cause : pendant
   une attente, `useAppsEnCours` relit toutes les 2 s, et chaque tick annulait la
   lecture en vol. `GET /services/running` répond en 1,3 à 1,9 s au repos ; sous la
   charge d'un lancement, il dépasse 2 s et aucune réponse n'est plus retenue.
2. **Le quota de la page Statistiques** est seul sur sa ligne, dans une boîte
   `max-w-md` : deux tiers de ligne vides.

## Solution proposée

1. Une lecture en vol n'est plus annulée par le tick suivant : le tick est sauté tant
   qu'elle n'est pas revenue ; seul le démontage jette sa réponse.
2. Une première ligne « chiffres clés » : les six KPI en grille 3 × 2 sur deux tiers,
   le quota sur le dernier tiers ; empilés en largeur étroite.

## Critères d'acceptation

- [x] Un test de `useAppsEnCours.test.ts` lève « En lancement » avec une lecture plus
      lente que `CADENCE_ATTENTE_MS`
- [x] Le quota de `StatsView/index.tsx` partage sa ligne avec les KPI à partir de `xl`
- [x] Benjamin a validé le rendu

## Dépendances

Aucune.

## Estimation

1 jour au plus, selon les retours.

## Risques

Faibles : un hook et une mise en page.
