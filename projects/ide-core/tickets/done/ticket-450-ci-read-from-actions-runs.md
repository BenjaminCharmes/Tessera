---
agent: codeur
created: 2026-10-15
depends_on:
- ticket-449
estimated_days: 0.5
id: ticket-450
pr_number: null
priority: high
status: done
title: The CI verdict is read from workflow runs, which a fine-grained token can read
type: fix
---

# ticket-450 — Lire le verdict de CI dans les workflow runs

## Objectif

Un projet privé dont le jeton GitHub est un jeton fine-grained peut merger
sur CI verte : Tessera lit le verdict là où ce jeton a le droit de lire.

## Contexte

Suite du ticket-449, mesuré par make-your-call le 15/10 avec le jeton de
Tessera, après ajout des permissions Actions et Commit statuses en lecture :

- `commits/<sha>/check-runs` : toujours 403 — l'API Checks n'est pas
  ouverte aux jetons fine-grained, et l'interface ne propose aucune
  permission « Checks » ;
- `commits/<sha>/status` : 200 ;
- `actions/workflows` : 200 ;
- `actions/runs?head_sha=<sha>` : 200, avec le verdict
  (`status: completed`, `conclusion: success`).

`_get_ci_status` dans `backend/src/tessera/services/github_service.py` ne
lit que `check-runs`. Tant que c'est le cas, aucun projet privé ne merge sur
CI verte avec ce jeton.

## Solution proposée

- `_get_ci_status` lit `GET /repos/{repo}/actions/runs?head_sha=<sha>` :
  aucun run → `"none"` ; un run dont `status` n'est pas `completed` →
  `"pending"` ; une `conclusion` parmi `failure`, `timed_out`, `cancelled`,
  `action_required` → `"failing"` (ou `"pending"` pour `action_required`,
  comme aujourd'hui) ; sinon `"passing"`.
- Repli sur `check-runs` seulement si `actions/runs` répond 403 ou 404 ;
  si les deux sont refusés, `"unreadable"` (ticket-449).
- Le message d'arrêt du ticket-449 nomme les permissions **Actions** et
  **Commit statuses** en lecture, et plus « Checks ».

## Critères d'acceptation

- [x] Un test vérifie que des runs `completed`/`success` sur le SHA donnent
      `"passing"` sans appeler `check-runs`
- [x] Un test vérifie qu'un run `in_progress` donne `"pending"`, et un run
      `completed`/`failure` donne `"failing"`
- [x] Un test vérifie qu'un 403 sur `actions/runs` suivi d'un 200 sur
      `check-runs` garde le verdict de `check-runs`
- [x] Un test vérifie qu'un 403 sur les deux donne `"unreadable"`
- [x] Le message d'arrêt de `backend/src/tessera/services/livraison.py`
      contient « Actions » et « Commit statuses », et plus « Checks »

## Ce que ça ne fait pas

- Ne lit pas les statuts de commit (`commits/<sha>/status`) des CI
  extérieures à GitHub Actions.