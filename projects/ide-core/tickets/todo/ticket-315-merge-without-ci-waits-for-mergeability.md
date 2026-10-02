---
id: ticket-315
title: "Merging without CI waits until GitHub knows whether the PR is mergeable"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-02
---

# ticket-315 — Merger sans CI attend que GitHub sache si la PR est fusionnable

## Objectif

Qu'un projet en `merge_without_ci` merge sa PR au lieu d'échouer en 405 juste
après l'avoir ouverte.

## Contexte

Le 2026-10-02, la livraison du ticket-016 de `carriere` s'est arrêtée sur :

```
Client error '405 Method Not Allowed' for url
'https://api.github.com/repos/BenjaminCharmes/carriere/pulls/18/merge'
```

`carriere` déclare `merge_without_ci: true` (ADR-045) : la livraison appelle
donc le merge aussitôt la PR ouverte. À cet instant, GitHub calcule encore si
la PR est fusionnable (`mergeable: null`), et il refuse. Quelques minutes plus
tard, la même PR était `MERGEABLE` et s'est mergée sans difficulté.

## Solution proposée

- Avant le merge, `GitHubService` lit la PR. Tant que `mergeable` vaut `null`,
  il attend et relit, dans une limite bornée (par exemple 60 secondes).
- `mergeable: false` arrête la livraison avec un `arret` qui le dit, sans
  appeler le merge.
- Un 405 au merge est retenté une fois après cette attente, puis remonté
  dans `arret`.

## Critères d'acceptation

- [ ] Un test (`respx`) vérifie qu'une PR lue d'abord avec `mergeable: null`,
      puis `true`, est mergée
- [ ] Un test vérifie qu'une PR `mergeable: false` n'appelle pas l'endpoint
      de merge, et que l'`arret` le dit
- [ ] Un test vérifie que l'attente est bornée : une PR qui reste à `null`
      arrête la livraison avec un `arret`, sans boucler
- [ ] Un test vérifie qu'un 405 suivi d'un succès au second essai mène au
      merge

## Dépendances

Aucune. Le ticket-306 déplace la phase de merge dans `CIWatcher` : le
correctif se place dans `GitHubService`, utilisé par les deux.
