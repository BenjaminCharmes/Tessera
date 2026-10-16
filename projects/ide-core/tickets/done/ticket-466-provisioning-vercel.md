---
agent: codeur
created: 2026-10-16
depends_on:
- ticket-465
estimated_days: 1.5
id: ticket-466
pr_number: 489
priority: medium
status: done
title: The Vercel step finds or creates the project, links its repository, adds the
  domain and writes missing variables without overwriting
type: feat
---

# ticket-466 — Étape Vercel : projet, domaine, variables, redéploiement

## Objectif

Le client Vercel et ses deux étapes (`vercel_project`, `variables`, puis
`redeploy`), plus l'`env_writer` que les autres services utilisent pour poser
leurs secrets.

## Contexte

ADR-053. Une variable Vercel de type `sensitive` ne se relit pas : on n'en
connaît que le nom. D'où la règle : poser **seulement si absente**, jamais
écraser. Avant d'écrire le client, relire la documentation de l'API REST
Vercel (projets, variables d'environnement, domaines, déploiements) et citer
les pages dans la docstring du module. Appels via `httpx` ; les tests utilisent
`httpx.MockTransport`, jamais le réseau.

## Solution proposée

- `VercelClient` (`services/provisioning/vercel.py`) : jeton et
  `VERCEL_TEAM_ID` lus dans `Settings` ; l'en-tête `Authorization` n'est ni
  loggé ni dans une erreur.
- `vercel_project` : cherche par nom (identifiant du projet), crée sinon avec le
  dépôt `github_remote`, ajoute le domaine s'il manque et verse les
  enregistrements DNS demandés dans `ctx.wanted_dns`.
- `variables` : `NEXT_PUBLIC_APP_URL`, `SESSION_SECRET`, `CRON_SECRET` (générés
  par `secrets.token_urlsafe`), posés si absents, en `sensitive` sauf la
  variable publique.
- `redeploy` : redéploie le dernier déploiement de production, seulement si
  `ctx.changed_env` n'est pas vide.

## Critères d'acceptation

- [ ] Un test vérifie qu'un projet Vercel trouvé par son nom n'est pas recréé
      (aucune requête de création) et qu'un projet absent est créé avec le
      dépôt de `github_remote`
- [ ] Un test vérifie que le domaine est ajouté s'il manque, et que les
      enregistrements DNS demandés arrivent dans `ctx.wanted_dns`
- [ ] Un test vérifie qu'une variable absente est écrite en `sensitive`, et
      qu'une variable existante n'est jamais réécrite
- [ ] Un test vérifie que le redéploiement n'est appelé que si une variable a
      été écrite pendant la relance
- [ ] Un test vérifie que sans `VERCEL_TOKEN` l'étape rend `needs_human` sans
      aucune requête
- [ ] Un test vérifie que ni le jeton ni une valeur de variable n'apparaissent
      dans les logs ni dans une `ServiceError`

## Ce que ça ne fait pas

Ne supprime rien. Ne crée ni équipe ni compte. Ne touche pas aux variables
d'un autre projet.

## Dépendances

ticket-465.