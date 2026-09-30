---
agent: codeur
created: 2026-09-30
depends_on: []
estimated_days: 0.5
id: ticket-265
pr_number: null
priority: high
status: done
title: Delivery merges ticket pull requests with the project's merge method, squash
  by default
type: fix
---

# ticket-265 — La livraison merge avec la méthode du projet, squash par défaut

## Objectif

Qu'une PR de ticket mergée par la livraison le soit comme le veut le dépôt :
en squash sur ce dépôt, et selon ce que déclare chaque projet ailleurs.

## Contexte

Constaté le 2026-09-30 : la PR #134 (ticket-262) est le premier merge fait
seul par la livraison, et elle a produit un **merge commit** (« Merge pull
request #134 »). `develop` a reçu les quatre commits du run — feat, docs, deux
bookkeeping — plus le merge.

`CLAUDE.md` impose le **squash** pour `ticket-XXX` → `develop`. Mais
`GitHubService.merge_pull_request` (`services/github_service.py`) envoie
`{"merge_method": "merge"}` en dur. L'écart n'avait jamais été vu : jusqu'au
ticket-260, la livraison ne mergeait jamais.

## Solution proposée

- `merge_pull_request` accepte un paramètre `method` (`squash`, `merge`,
  `rebase`), transmis à l'API.
- `agents.json` peut déclarer `merge_method` ; lu par `PolitiqueRun`
  (`services/politique_run.py`) comme `base_branch`. **Absent ou inconnu :
  `squash`.**
- En squash, le titre du commit est celui de la PR (déjà conforme depuis le
  ticket-259) suivi de ` (#N)`, comme un squash fait depuis l'interface :
  passer `commit_title` à l'API.
- La PR de release `develop` → `main` n'est pas concernée : la livraison ne
  l'ouvre pas.

## Critères d'acceptation

- [ ] Un test montre que `merge_pull_request` envoie `merge_method: "squash"`
      quand on lui passe `method="squash"`.
- [ ] Un test montre qu'un projet sans `merge_method` dans `agents.json` est
      mergé en `squash` par la livraison.
- [ ] Un test montre qu'un projet déclarant `"merge_method": "merge"` est mergé
      en `merge`.
- [ ] Un test montre qu'une valeur inconnue retombe sur `squash`.

## Dépendances

Aucune.

## Estimation

Une demi-journée. Backend uniquement.

## Risques

- Le squash rend nécessaire le ticket-264 pour les files : sans lui, le ticket
  suivant d'une file porte les commits du précédent, que le squash a remplacés.