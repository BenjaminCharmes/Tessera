---
agent: codeur
created: 2026-10-16
depends_on:
- ticket-466
estimated_days: 1
id: ticket-467
pr_number: 490
priority: medium
status: done
title: The database step finds or creates the Neon project and hands its connection
  URL to Vercel without ever returning it
type: feat
---

# ticket-467 — Étape base de données (Neon)

## Objectif

Qu'un projet en ligne ait sa base et que `DATABASE_URL` soit dans Vercel, sans
que l'URL (mot de passe compris) passe ailleurs que d'une API à l'autre.

## Contexte

ADR-053. Hypothèse retenue par l'architecte : la création de base passe par
l'**API Neon** (`NEON_API_KEY`). La documentation Vercel consultée ne montre
pas de point d'accès REST pour créer un stockage Marketplace — seulement le
tableau de bord et la CLI. Un compte Neon géré par l'intégration Vercel n'a
peut-être pas de clé d'API : l'étape a donc un repli explicite, `manual`, qui
vérifie seulement la présence de `DATABASE_URL`. Relire la documentation Neon
(projets, URI de connexion) avant d'écrire le client ; citer les pages dans la
docstring.

## Solution proposée

- `NeonClient` (`services/provisioning/neon.py`), même discipline d'erreurs et
  de logs que le client Vercel.
- Étape `database` : projet Neon cherché par nom (identifiant du projet) ;
  absent → créé ; l'URI de connexion est lue par l'API et passée à
  `ctx.env_writer.set_env("DATABASE_URL", …)`, inscrite dans `SecretRegistry`.
- `DATABASE_URL` déjà dans Vercel : `skipped`, sans appel à Neon.
- Deux projets Neon du même nom : `failed`, rien n'est créé.

## Critères d'acceptation

- [ ] Un test vérifie qu'un projet Neon existant n'est pas recréé et qu'un
      projet absent est créé, l'URI étant écrite dans Vercel sous `DATABASE_URL`
- [ ] Un test vérifie qu'avec `DATABASE_URL` déjà dans Vercel l'étape rend
      `skipped` sans requête vers Neon
- [ ] Un test vérifie qu'un projet Neon existant sans `DATABASE_URL` dans
      Vercel retrouve l'URI par l'API et l'écrit
- [ ] Un test vérifie que deux projets Neon du même nom rendent `failed` sans
      création
- [ ] Un test vérifie que sans `NEON_API_KEY` l'étape rend `manual` si
      `DATABASE_URL` existe, `needs_human` sinon, avec l'instruction
- [ ] Un test vérifie que l'URI n'apparaît ni dans les logs, ni dans un
      événement, ni dans une `ServiceError` dont le corps de réponse la répète

## Ce que ça ne fait pas

Ne supprime pas de base, ne migre pas de schéma (le projet le fait à son
déploiement).

## Dépendances

ticket-466 (`env_writer`).