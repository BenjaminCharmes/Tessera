---
agent: codeur
created: 2026-09-30
depends_on: []
estimated_days: 0.5
id: ticket-262
pr_number: null
priority: medium
status: done
title: Charts' screen-reader tables no longer stretch the stats page
type: fix
---

# ticket-262 — Les tableaux lus par lecteur d'écran n'allongent plus la page

## Objectif

Que la vue Statistiques ne défile pas sur une zone vide sous le dernier bloc.

## Contexte

Constaté le 2026-09-30 : la vue Statistiques défile loin sous « Runs récents »,
sur du vide. Mesuré dans le navigateur (fenêtre 1920×1000, période 30 j) : le
conteneur défilant fait 1410 px de haut pour 1373 px de contenu, et l'élément le
plus bas est un `<table class="sr-only">`. L'écart grandit avec la période :
sur 90 jours, le tableau de « Dépense par jour » porte 90 lignes.

La cause est dans `DataTable` (`frontend/src/design/charts/frame.tsx`) :
`sr-only` est posé **sur le `<table>` lui-même**. Or un tableau ignore
`height: 1px` et `overflow: hidden` — sa hauteur est un minimum, il grandit pour
contenir ses lignes. Le conteneur `relative` ajouté par un ticket précédent le
retient dans la zone qui défile, mais ne l'empêche pas de l'allonger.

## Solution proposée

- Poser `sr-only` sur un **`<div>` qui enveloppe** le tableau, pas sur le
  `<table>` : un bloc respecte `height: 1px` et `overflow: hidden`, et le
  tableau reste lisible par un lecteur d'écran.
- Mettre à jour le commentaire au-dessus : il explique aujourd'hui le
  conteneur `relative`, il doit dire pourquoi `sr-only` ne va pas sur la table.

## Critères d'acceptation

- [ ] Dans `DataTable`, la classe `sr-only` est portée par un élément `div`
      ancêtre du `<table>`, et plus par le `<table>`.
- [ ] Un test de `frame` (ou d'un graphique) montre que le `<table>` rendu par
      `DataTable` a un ancêtre portant la classe `sr-only`.
- [ ] Le tableau reste trouvable par `getByRole("table")` avec sa `caption`
      (test existant ou nouveau).

## Dépendances

Aucune.

## Estimation

Une demi-journée. Frontend uniquement.

## Risques

- Les tests qui cherchent `table.sr-only` ou le `data-testid="data-table"`
  sont à adapter sans perdre ce qu'ils vérifient.