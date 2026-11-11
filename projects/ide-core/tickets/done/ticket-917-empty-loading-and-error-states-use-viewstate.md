---
agent: codeur
created: 2026-11-11
depends_on: []
estimated_days: 0.5
id: ticket-917
pr_number: null
priority: low
status: done
title: Empty, loading and error states use the shared ViewState components
type: refactor
---

# ticket-917 — États vide, chargement et erreur : les vues passent par `ViewState`

## Objectif

Un même aspect pour « rien à montrer », « chargement » et « erreur » dans
toutes les vues.

## Contexte

`design/ui/ViewState.tsx` exporte `Vide`, `Chargement` et `Erreur`
(ticket-439), mais seul `design/ui/ui.test.tsx` l'importe : aucune vue ne
s'en sert. Chaque vue refait ses états, avec quatre tailles de texte et deux
gris :

- `components/FichiersView/Sections.tsx` et `components/FichiersView/index.tsx` ;
- les `Message` locaux de `components/HistoriqueView/index.tsx` et
  `components/ProjetsView/index.tsx` ;
- `components/StatsView/RunHistorique.tsx`, `components/StatsView/index.tsx` ;
- `components/CenterView.tsx`.

## Solution proposée

Remplacer ces états par `Vide`, `Chargement` ou `Erreur`, en gardant le texte
français actuel de chaque vue comme `titre` ou `phrase`.

## Critères d'acceptation

- [ ] `HistoriqueView/index.tsx`, `ProjetsView/index.tsx`,
      `FichiersView/Sections.tsx`, `FichiersView/index.tsx`,
      `StatsView/index.tsx` et `StatsView/RunHistorique.tsx` importent au moins
      un composant de `design/ui/ViewState`.
- [ ] Les fonctions `Message` locales de `HistoriqueView/index.tsx` et
      `ProjetsView/index.tsx` ont disparu.
- [ ] Le diff ne laisse dans ces fichiers aucun `<p>` portant « Chargement… ».
- [ ] Les tests de ces vues passent, adaptés si un texte ou un rôle a changé.

## Ce que ça ne fait pas

Ne touche ni au Bureau ni aux modales.

## Dépendances

Aucune.

## Estimation

Une demi-journée.

## Risques

`Chargement` rend des lignes squelettes, pas un texte : un test qui cherchait
« Chargement… » doit chercher le rôle ou l'étiquette accessible.