---
id: ticket-164
title: "« Select a project » s'affiche en anglais, sur un projet déjà sélectionné"
type: fix
status: in-review
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-25
---

# ticket-164 — « Select a project », deux fois faux

## Objectif

Qu'un run sélectionné dans la Supervision montre son panneau, en français.

## Contexte

Dans la vue Supervision, une carte de run sélectionnée affiche au centre
« Select a project » — alors qu'un run *est* sélectionné, et que tout le reste
de l'interface est en français.

Deux défauts sur une ligne, `AgentPanel/index.tsx` :

```tsx
{project ? "Lance un ticket pour commencer" : "Select a project"}
```

1. La chaîne n'a jamais été traduite.
2. Elle s'affiche parce que `SupervisionView` construit son projet par
   `projects.find((p) => p.id === selectionne.project_id) ?? null`. Quand la
   recherche échoue, le panneau reçoit `null` et rend le message du cas « aucun
   projet » — alors que la carte, elle, sait parfaitement de quel projet il
   s'agit.

Faire dépendre l'affichage d'une correspondance qui peut manquer, quand
l'information est déjà là, c'est perdre deux fois : l'utilisateur ne voit pas
son run, et le message lui demande ce qu'il vient de faire.

## Solution proposée

1. Traduire la chaîne.
2. Un run sélectionné montre son panneau même si la recherche échoue : le
   `project_id` de la carte suffit à l'identifier.

## Critères d'acceptation

- [ ] Aucune chaîne d'interface anglaise ne subsiste dans `AgentPanel`
- [ ] Un run sélectionné dont le projet est absent de la liste affiche quand
      même son panneau, et pas « sélectionne un projet »
- [ ] `npx vitest run`, `tsc` et `eslint` passent

## Dépendances

Aucune.

## Estimation

Moins d'une journée.

## Risques

Le repli masque une liste de projets vide au lieu de la signaler. C'est le bon
compromis ici : la Supervision sert à regarder des runs, pas à diagnostiquer le
chargement des projets.
