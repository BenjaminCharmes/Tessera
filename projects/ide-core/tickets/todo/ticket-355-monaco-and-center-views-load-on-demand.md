---
id: ticket-355
title: "Monaco and the center views load on demand instead of at startup"
type: fix
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-05
---

# ticket-355 — Monaco et les vues centrales se chargent à la demande

## Objectif

Que l'application démarre et affiche sa première vue sans attendre Monaco ni
des vues que l'utilisateur n'a pas ouvertes.

## Contexte

`frontend/src/main.tsx` importe tout `monaco-editor` et trois workers
(éditeur, JSON, TypeScript) au démarrage, et appelle `loader.config`.
`frontend/src/components/CenterView.tsx` importe toutes les vues d'avance
(`DiffView`, `StatsView`, `SupervisionView`, `RunView`, `Editor`,
`KanbanView`, `ChatPanel`). Il n'existe aucun `React.lazy` ni `import()`
dynamique dans `src/`, et `vite.config.ts` n'a pas de `manualChunks`.

ADR-012 impose Monaco bundlé depuis `monaco-editor` via Vite, sans CDN :
cela reste vrai, seul le moment du chargement change.

## Solution proposée

1. Déplacer la configuration Monaco (`MonacoEnvironment`, workers,
   `loader.config`) de `main.tsx` vers un module `frontend/src/lib/monaco.ts`,
   importé dynamiquement par le composant d'éditeur avant son premier rendu.
2. `CenterView` charge chaque vue par `React.lazy`, sous un `Suspense` avec un
   état de chargement sobre (`zinc`, ADR-026). La vue affichée par défaut peut
   rester importée statiquement.
3. `vite.config.ts` isole `monaco-editor` dans son propre chunk
   (`build.rollupOptions.output.manualChunks`).

## Critères d'acceptation

- [ ] `main.tsx` n'importe plus `monaco-editor` ni ses workers
- [ ] `lib/monaco.ts` existe et porte `MonacoEnvironment` et
      `loader.config`
- [ ] `CenterView.tsx` utilise `React.lazy` pour au moins `DiffView`,
      `StatsView`, `Editor` et `ChatPanel`
- [ ] `vite.config.ts` déclare un `manualChunks` qui place `monaco-editor`
      dans un chunk à part
- [ ] Un test de rendu de `CenterView` montre qu'une vue paresseuse s'affiche
      après résolution de son chargement

## Dépendances

Aucune.

## Estimation

Une demi-journée.

## Risques

Les tests qui rendent une vue paresseuse doivent attendre (`findBy…`) au lieu
de lire l'écran aussitôt.
