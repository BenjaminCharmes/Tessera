---
id: ticket-258
title: "Drop the unused per-project usage fetch, and show the stats scope actually applied"
type: refactor
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-09-30
---

# ticket-258 — Retirer la lecture d'usage devenue morte, afficher la portée réelle

## Objectif

Supprimer ce que le ticket-253 a rendu inutile, et faire dire au sélecteur de
portée la portée réellement appliquée.

## Contexte

Relu après le merge du ticket-253 :

- `hooks/useCockpit.ts` appelle encore `useUsage(project?.id ?? null)` et passe
  `usage`, `loading`, `error` dans le groupe `usage` des props de la colonne
  (`UsageSidebar`, `components/Sidebar/index.tsx`). Depuis que la colonne rend
  `PanneauUsage`, **aucun composant ne lit ces trois champs** : c'est un appel
  réseau à chaque changement de projet, pour rien.
- Sans projet actif, `statsPortee` reste `"projet"` : `CenterView` reçoit bien
  `statsProjectId = null` (tous projets), mais `PanneauUsage` affiche « Ce
  projet » pressé et grisé, « Tous les projets » non pressé. L'écran contredit
  ce qu'il montre.

## Solution proposée

- Retirer `usage`, `loading`, `error` de `UsageSidebar` et de sa construction
  dans `useCockpit`. Retirer l'appel `useUsage` et son `refresh`. Si
  `hooks/useUsage.ts` n'a plus aucun appelant, le supprimer avec son test ; ne
  pas toucher `api.usage` ni le type `ProjectUsage` s'ils servent ailleurs.
- Calculer une portée **effective** dans `useCockpit` : `"tous"` quand aucun
  projet n'est actif, sinon l'état choisi. `PanneauUsage` et `statsProjectId`
  lisent tous deux cette portée effective.

## Critères d'acceptation

- [ ] `UsageSidebar` ne déclare plus les champs `usage`, `loading` ni `error`.
- [ ] `hooks/useCockpit.ts` n'importe plus `useUsage`.
- [ ] Un test de `PanneauUsage` (ou de `Sidebar`) montre que, sans projet actif,
      le bouton « Tous les projets » a `aria-pressed="true"`.
- [ ] Aucun fichier du dépôt n'importe `hooks/useUsage` sans que ce fichier
      existe (le diff supprime l'un et l'autre, ou garde les deux).

## Dépendances

Aucune — ticket-253 est mergé.

## Estimation

Une demi-journée. Frontend uniquement.

## Risques

- Les fixtures de `SidebarChat.test.tsx` et `PanneauUsage.test.tsx`
  construisent le groupe `usage` : retirer les trois champs des fixtures.
