---
id: ticket-317
title: "The SupervisionView selection test is flaky under load"
type: fix
status: todo
priority: low
agent: codeur
pr_number: null
depends_on: []
estimated_days: 0.5
created: 2026-10-02
---

# ticket-317 — Le test de sélection de SupervisionView est instable sous charge

Constaté le 2026-10-02 : ce test a échoué une fois pendant la vérification du
ticket-310, alors que la machine faisait aussi tourner un modèle local. Lancé
seul sur `develop`, il passe trois fois sur trois. Ce ticket cherche donc une
dépendance au temps (clic non attendu, `waitFor` trop court), pas un bogue
du composant.

## Symptôme

```
FAIL  src/components/SupervisionView/SupervisionView.test.tsx
✗  selectionne un run au clic, ce qui declenche son abonnement
AssertionError: expected "vi.fn()" to be called with arguments: [ 'run-2' ]
```

Le test clique sur la carte ayant l'`aria-label` `"Run ticket-001 sur portfolio"` (qui
correspond à `run_id: "run-2"`) et attend que `selectionner("run-2")` soit
appelé. La `vi.waitFor` n'aboutit pas : soit `selectionner` n'est pas appelé,
soit elle l'est avec un mauvais argument.

## Contexte

`SupervisionView/index.tsx` ligne 101 :
```tsx
onSelect={() => selectionner(run.run_id)}
```

`RunCard.tsx` ligne 63 :
```tsx
aria-label={`Run ${run.ticket_id ?? run.mode} sur ${run.project_id}`}
```

Les deux lignes sont cohérentes avec l'intention du test. La cause probable
est l'une des suivantes :

1. `selectionner` est court-circuité par `suivre` — le hook `UseSupervisionResult`
   expose maintenant `suivre: vi.fn()` et `observerLeTexte: vi.fn()` que le
   composant pourrait appeler (via un `useEffect` non visible ou depuis un
   composant enfant) à la place ou avant `selectionner`.
2. Le `userEvent.click` est émis en `void` (non attendu) et le DOM n'est pas
   encore mis à jour quand la `vi.waitFor` commence — le timing dépend de la
   version de `@testing-library/user-event`.
3. Une auto-sélection du premier run (`runs[0]`) par effet de bord appelle
   `selectionner("run-1")` après le clic, masquant l'appel avec `"run-2"`.

## Ce qui est à faire

1. Reproduire localement avec `npx vitest run --reporter verbose
   src/components/SupervisionView/SupervisionView.test.tsx`
2. Identifier si `selectionner` est jamais appelé (ajouter un
   `console.log` temporaire dans le mock) et avec quels arguments
3. Corriger le composant **ou** le test — selon où est le vrai bogue
4. S'assurer que toute la suite `SupervisionView.test.tsx` passe

## Critères d'acceptation

- [ ] Le test `"selectionne un run au clic, ce qui declenche son abonnement"`
      passe
- [ ] Aucun autre test `SupervisionView` ne régresse
- [ ] `npm run test` passe en entier

## Ce que ça ne fait pas

Ce ticket ne touche pas à la logique de sélection côté hook (`useSupervision`)
si le bug est dans le test lui-même.
