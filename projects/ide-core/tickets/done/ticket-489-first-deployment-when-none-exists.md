---
agent: codeur
created: 2026-10-16
depends_on: []
estimated_days: 0.5
id: ticket-489
pr_number: null
priority: high
status: done
title: Putting a project online triggers its first production deployment when Vercel
  has none
type: fix
---

# ticket-489 — Premier déploiement quand Vercel n'en a aucun

## Objectif

À la fin d'une mise en ligne, le projet a au moins un déploiement de
production, même quand aucune variable n'a changé pendant le run.

## Contexte

16/10, première mise en ligne réelle (devinoo) : projet Vercel créé et relié
au dépôt, base branchée, variables posées, domaine vérifié, DNS publiés…
mais aucun déploiement. `VercelRedeployStep`
(`backend/src/tessera/services/provisioning/vercel_steps.py`) rend `skipped`
avec « no variable was written » : il ne redéploie que si une variable a
changé, et ne voit pas qu'il n'existe aucun déploiement à refaire. Créer un
projet par l'API ne déploie pas.

Le déploiement a été lancé à la main par
`POST /v13/deployments?skipAutoDetectionConfirmation=1` avec
`gitSource: {type: "github", repoId, ref: <base>}` et `target: production` :
sans `skipAutoDetectionConfirmation`, Vercel répond 400
`missing_project_settings` pour un projet neuf.

## Solution proposée

`VercelRedeployStep` lit les déploiements de production du projet
(`GET /v6/deployments?projectId=…&target=production&limit=1`) :
- aucun déploiement : en créer un depuis la branche de base, avec
  `skipAutoDetectionConfirmation=1`, `gitSource` (identifiant du dépôt
  GitHub lu par l'API GitHub), et rendre `pending` jusqu'à `READY` ;
- un déploiement existe et une variable a changé : redéployer comme
  aujourd'hui ;
- sinon : `skipped`.
Un déploiement en `ERROR` rend l'étape `failed` avec le code d'erreur de
Vercel, sans le journal de build.

## Critères d'acceptation

- [ ] Un test vérifie qu'un projet sans déploiement de production en reçoit
      un, avec `skipAutoDetectionConfirmation=1` et la branche de base
- [ ] Un test vérifie qu'un projet déjà déployé sans variable changée reste
      `skipped`
- [ ] Un test vérifie qu'un déploiement en `ERROR` rend `failed` avec le code
      d'erreur
- [ ] Un test vérifie que l'identifiant du dépôt vient de `github_remote`