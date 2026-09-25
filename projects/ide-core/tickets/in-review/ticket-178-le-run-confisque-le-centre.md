---
id: ticket-178
title: "Un run en cours confisque le centre, et « Vue liste » n'a plus d'effet"
type: fix
status: in-review
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-25
---

# ticket-178 — Le run confisque le centre

## Objectif

Qu'on puisse regarder autre chose pendant qu'un run tourne.

## Contexte

Pendant un run, le bouton « Vue liste » de l'onglet Tickets ne fait plus rien.
Le tableau et la liste sont tous deux inatteignables jusqu'à la fin du run.

Le centre d'`App.tsx` est une cascade de priorités :

```tsx
(stream.status === "running" || "connecting") && !openFilePath && !showDiff
  ? <RunView />          // ← gagne toujours
  : showDiff ? <DiffView />
  : showKanban ? <KanbanView />
  : <Editor />
```

`RunView` est testé **avant** le Kanban. `onToggleKanban` bascule bien
`showKanban`, mais la branche n'est jamais atteinte : le clic est sans effet,
sans que rien ne l'explique.

La cascade traite `openFilePath` et `showDiff` comme des choix de
l'utilisateur — le basculement les efface d'ailleurs — mais la vue du run comme
un **état dérivé** de `stream.status`. Or c'est aussi une vue parmi d'autres.
Un choix qui ne peut pas s'exprimer n'est pas un choix.

## Solution proposée

Le centre montre **ce que l'utilisateur a demandé en dernier**. Un run qui
démarre amène sa vue au premier plan — c'est utile, c'est ce qu'on veut voir —
mais tout geste explicite la reprend. `RunView` reste atteignable tant que le
run tourne.

## Critères d'acceptation

- [ ] Pendant un run, « Vue liste » et « Vue tableau » changent bien le centre
- [ ] Un run qui démarre affiche sa vue sans qu'on la demande
- [ ] Après avoir basculé, la vue du run reste atteignable
- [ ] Ouvrir un fichier ou un diff garde son comportement
- [ ] La fin d'un run ne ramène pas de force une vue qu'on venait de quitter
- [ ] `npx vitest run`, `tsc` et `eslint` passent

## Dépendances

Aucune.

## Estimation

Moins d'une journée.

## Risques

Remplacer une cascade de booléens par un état nommé touche au centre de l'app.
Le garde-fou est que chaque vue reste joignable par le geste qui l'ouvrait
déjà.
