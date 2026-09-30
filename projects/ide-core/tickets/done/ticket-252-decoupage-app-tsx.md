---
id: ticket-252
title: "App.tsx redescend sous 200 lignes, les props par domaine"
type: refactor
status: done
pr_number: null
priority: low
agent: codeur
depends_on: ["ticket-250"]
estimated_days: 2
created: 2026-09-29
---

# ticket-252 — App.tsx redescend sous 200 lignes, les props par domaine

## Objectif

Découper `App.tsx` (428 lignes, ~50 props passées à `Sidebar`) pour revenir
sous la règle des 200 lignes et rendre lisible qui dépend de quoi.

## Contexte

`App.tsx` tient la grille, la sélection du panneau, la vue du centre, et
relaie l'état de tous les domaines (tickets, runs, file, chat, services) vers
`Sidebar` en props individuelles. ADR-013 avait écarté un store « à réévaluer
si on dépasse 5 états globaux partagés » — le seuil est atteint, mais
introduire Zustand est une décision d'architecture à part : ce ticket s'en
tient à React (contextes par domaine), et laisse la réévaluation d'ADR-013 à
un ADR dédié si les contextes ne suffisent pas.

## Solution proposée

Extraire de `App.tsx` : la vue du centre (un composant `CenterView` qui porte
le `switch`), la grille (dimensions dans `design/layout.ts`, plus en `style`
en dur), et le graphe d'état dans un hook `useCockpit` qui rend des **props
groupées par domaine** (`projet`, `tickets`, `runs`, `usage`, `chat`,
`fichiers`, `agents`). Retenu à l'implémentation plutôt que des contextes :
mêmes groupes, mais `Sidebar` reste testable sans providers et le flux de
données reste explicite. Pas de nouvelle dépendance.

## Critères d'acceptation

- [ ] `App.tsx` fait moins de 200 lignes
- [ ] `Sidebar` reçoit moins de 10 props
- [ ] Les dimensions de la grille viennent de `design/layout.ts`, plus d'un `style` en dur dans `App.tsx`
- [ ] Le `switch` de la vue du centre vit dans un composant dédié
- [ ] Les tests existants d'`App` et de `Sidebar` passent, adaptés aux props groupées

## Dépendances

- ticket-250 (le déplacement des conversations change les props concernées)

## Estimation

2 jours.

## Risques

Refactor large sans changement visuel : le diff doit rester mécanique
(déplacement, pas réécriture) pour rester relisible.

`useCockpit` concentre le graphe entier (~360 lignes) : au-dessus de la
préférence des 200, assumé — c'est un déplacement, pas une réécriture. Le
découper davantage, ou passer à un store, est la réévaluation qu'ADR-013
réserve à un ADR dédié.
