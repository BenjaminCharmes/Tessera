---
id: ticket-503
title: "Putting a project online ends with a declared health check that reaches the database"
type: feat
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-10-18
---

# ticket-503 — La mise en ligne finit par un contrôle de santé qui touche la base

## Objectif

Une mise en ligne ne se déclare terminée que si le site répond **et** si une
route qui lit la base répond, pour qu'une base vide ou injoignable soit vue le
jour même.

## Contexte

18/10, Kadoomi : la mise en ligne s'est dite terminée, toutes les pages
répondaient 200, mais la base de production n'avait aucune table : le build
(`prisma generate && next build`) n'appliquait pas les migrations. La
connexion par e-mail renvoyait 500. Rien dans le plan
(`vercel_project` … `redeploy`) ne touche la base une fois déployée. Signalé
par la session Kadoomi ; Devinoo n'avait pas le problème (son build fait
`prisma migrate deploy`).

## Solution proposée

1. Le bloc `online` d'`agents.json` accepte `health_path` (facultatif, ex.
   `"/api/health"`) : une route du projet qui lit au moins une table et rend
   200 si tout va bien.
2. Une dernière étape `health_check`, après `redeploy` : `GET
   https://<domaine><health_path>`, avec quelques essais espacés le temps que
   le déploiement réponde. 200 → `done` ; autre statut ou délai dépassé →
   `failed`, avec le statut et les 200 premiers caractères de la réponse.
3. Sans `health_path` : l'étape vérifie seulement que `https://<domaine>/`
   répond 200, et le dit dans son détail (« base non vérifiée : déclarer
   health_path »).
4. `docs/architecture.md`, section « Déclaration par projet », documente
   `health_path`.

## Ce que ça ne fait pas

- N'écrit pas la route de santé du projet : c'est un ticket du projet.
- N'applique pas les migrations : c'est le build du projet qui le fait.

## Critères d'acceptation

- [ ] Un test vérifie que `health_path` est lu depuis le bloc `online`
- [ ] Un test vérifie qu'une route de santé en 200 rend l'étape `done`
- [ ] Un test vérifie qu'un 500 de la route rend l'étape `failed` avec le statut
      dans le détail
- [ ] Un test vérifie que, sans `health_path`, l'étape contrôle `/` et le
      signale dans son détail
- [ ] `docs/architecture.md` décrit `health_path`
