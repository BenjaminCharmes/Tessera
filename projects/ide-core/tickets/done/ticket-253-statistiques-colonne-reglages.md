---
agent: codeur
created: 2026-09-30
depends_on: []
estimated_days: 1
id: ticket-253
pr_number: null
priority: medium
status: done
title: 'Stats column holds the view''s settings: period, scope and spending limits'
type: feat
---

# ticket-253 — La colonne des statistiques porte les réglages de la vue

## Objectif

Rendre utile la colonne latérale de l'onglet Statistiques en y plaçant ce qui
règle la vue centrale, pour que le centre ne montre plus que des chiffres.

## Contexte

Depuis le ticket-250, le détail des coûts vit au centre (`StatsView`) et la
colonne n'affiche plus qu'une ligne — « $X sur N runs — détail au centre »
(`components/Sidebar/index.tsx`, branche `panel === "usage"`). La grille garde
pourtant 280 px à cette colonne (`design/layout.ts`) : l'espace est presque vide.

Deux réglages existent déjà ou manquent :
- la **période** (7 / 30 / 90 j) est un état local de `StatsView`, rendu dans
  son bandeau d'en-tête ;
- la **portée** « ce projet / tous projets » n'existe pas : `CenterView` passe
  `project?.id ?? null`, si bien que voir la vue globale oblige à désélectionner
  le projet.

Les **plafonds de dépense** (`useLimites`, `GET /orchestrator/limits`) ne sont
visibles nulle part à côté de la dépense qu'ils bornent.

**Les chiffres clés (`KpiRow`) restent en haut du centre** : décision
utilisateur, ils ne bougent pas.

## Solution proposée

- Remonter l'état de la période hors de `StatsView` (dans `useCockpit`, là où
  vit déjà l'état partagé — pas de store, ADR-013). `StatsView` reçoit `days`
  en prop.
- Ajouter un état de portée : `"projet"` (défaut quand un projet est actif) ou
  `"tous"`. `CenterView` passe `projectId = null` quand la portée est `"tous"`.
- Dans la colonne, branche `panel === "usage"`, remplacer la ligne de résumé par
  trois blocs empilés :
  1. **Période** : le sélecteur 7 / 30 / 90 j, déplacé depuis le bandeau de
     `StatsView` (même style de boutons `aria-pressed`, même libellé « jours UTC »).
  2. **Portée** : deux boutons « Ce projet » / « Tous les projets ». Sans projet
     actif, « Ce projet » est désactivé et la portée vaut « tous ».
  3. **Plafonds** : les valeurs de `useLimites` — plafond par run
     (`run_max_budget_usd`) et plafond global (`llm_max_budget_usd`), `0`
     affiché « aucun plafond ».
- Le bandeau de `StatsView` garde son titre et perd le sélecteur de période.
- Couleurs : ADR-026 — sélection en fond, jamais de violet en texte.

## Critères d'acceptation

- [ ] Le sélecteur de période n'est plus rendu dans `StatsView` ; il est rendu
      dans la colonne latérale quand `panel === "usage"`, et changer de période
      recharge `api.usage.stats` avec le nouveau nombre de jours (test dans
      `Sidebar` ou `StatsView` qui le vérifie).
- [ ] Un bouton « Tous les projets » dans la colonne fait appeler
      `api.usage.stats` avec `projectId = null` alors qu'un projet est actif
      (test qui le vérifie).
- [ ] Sans projet actif, le bouton « Ce projet » est désactivé (test).
- [ ] La colonne affiche les deux plafonds de `useLimites`, et « aucun plafond »
      pour une valeur `0` (test).
- [ ] `KpiRow` reste rendu en haut de `StatsView`.
- [ ] Aucune classe `text-violet-*` n'est ajoutée (le test de cohérence existant
      le vérifie déjà).

## Dépendances

Aucune.

## Estimation

1 jour. Frontend uniquement.

## Risques

- `SidebarChat.test.tsx` et `StatsView.test.tsx` construisent les props
  groupées de la colonne : les fixtures sont à mettre à jour avec les nouveaux
  champs.
- Ne pas dupliquer les plafonds s'ils sont déjà affichés ailleurs (panneau des
  réglages du pipeline) : ici on les **montre**, on ne les édite pas.