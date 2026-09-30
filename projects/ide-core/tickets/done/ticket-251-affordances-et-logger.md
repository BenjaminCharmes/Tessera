---
id: ticket-251
title: "Icônes, en-têtes et logs passent par leur point central"
type: refactor
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-29
---

# ticket-251 — Icônes, en-têtes et logs passent par leur point central

## Objectif

Ramener dans leurs points centraux les affordances définies localement
(icônes, glyphes, bande d'en-tête) et donner au frontend le logger structuré
que la convention exige sans qu'il existe.

## Contexte

`NavRail.tsx:40-135` définit huit icônes SVG et sa grille `ICON` localement au
lieu de `design/icons.tsx` ; il écrit aussi `h-10` en dur au lieu de `BAND`.
`ChatPanel/index.tsx` ferme avec le glyphe `×` alors qu'`IconCross` existe
(hors des plages que le test surveille). L'en-tête d'`UsageDashboard` cité par
l'audit a disparu avec le composant (ticket-250). Enfin la convention interdit
`console.log` au profit d'un logger structuré… qui n'existe pas côté
frontend : `ErrorBoundary.tsx:22` appelle `console.error` faute d'outil.

## Solution proposée

Déplacer les huit icônes de NavRail dans `design/icons.tsx` (mêmes tracés,
grille de 24 conservée) ; NavRail importe, et sa zone d'identité passe par
`BAND`. Remplacer `×` par `IconCross`. Créer `lib/logger.ts` : niveaux
`debug/info/warn/error`, sortie JSON une ligne `{ts, level, msg, ...ctx}`,
seul module autorisé à appeler `console`. `ErrorBoundary` l'utilise.
Verrouiller trois fois : `coherence.test.ts` interdit `<svg` hors de
`design/` et ajoute `×` aux glyphes bannis ; ESLint `no-console` sur `src/`
avec exception pour `lib/logger.ts`.

## Critères d'acceptation

- [ ] Aucune balise `<svg>` n'est définie hors de `design/` ; un test de `coherence.test.ts` le verrouille
- [ ] Aucun caractère `×` ne sert de bouton dans `ChatPanel` ; `IconCross` le remplace et le glyphe rejoint les plages bannies du test
- [ ] `lib/logger.ts` existe, typé strict, avec un test par niveau exposé
- [ ] `eslint` refuse un `console.log` ajouté dans un composant, mais pas dans `lib/logger.ts`
- [ ] `ErrorBoundary` ne contient plus d'appel direct à `console`

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Le déplacement des icônes touche aussi les fixtures de tests de NavRail ;
les mettre à jour plutôt que de les dupliquer.
