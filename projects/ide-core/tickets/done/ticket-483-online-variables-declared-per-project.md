---
agent: codeur
created: 2026-10-16
depends_on: []
estimated_days: 0.5
id: ticket-483
pr_number: 508
priority: high
status: done
title: A project declares which variables provisioning generates and which it derives
  from the domain
type: feat
---

# ticket-483 — Variables générées et dérivées déclarées par projet

## Objectif

L'étape « Variables » de la mise en ligne pose les variables dont chaque
projet a besoin, au lieu d'une liste figée valable pour un seul projet.

## Contexte

Kadoomi, 16/10 : l'étape Variables
(`backend/src/tessera/services/provisioning/vercel_steps.py`,
`GENERATED_VARIABLES = ("SESSION_SECRET", "CRON_SECRET")`) génère les secrets
de Devinoo. Kadoomi utilise Better Auth, qui lit `BETTER_AUTH_SECRET` (secret
aléatoire) et `BETTER_AUTH_URL` (`https://kadoomi.com`) : sans elles, la
connexion casse en production.

## Solution proposée

Le bloc `online` d'`agents.json` accepte deux clés facultatives :
- `"generate": ["BETTER_AUTH_SECRET", "CRON_SECRET"]` : secrets aléatoires
  (`secrets.token_urlsafe(32)`), posés seulement si absents ;
- `"derive": {"BETTER_AUTH_URL": "https://{domain}"}` : valeurs calculées,
  avec `{domain}` remplacé par le domaine déclaré, posées seulement si
  absentes.
Sans `generate`, la liste actuelle (`SESSION_SECRET`, `CRON_SECRET`) reste le
défaut. `NEXT_PUBLIC_APP_URL` reste posée comme aujourd'hui.
`docs/architecture.md` (section « Déclaration par projet ») décrit les deux
clés.

## Critères d'acceptation

- [ ] Un test vérifie que `"generate": ["BETTER_AUTH_SECRET"]` pose
      `BETTER_AUTH_SECRET` et ne pose pas `SESSION_SECRET`
- [ ] Un test vérifie que `"derive": {"BETTER_AUTH_URL": "https://{domain}"}`
      pose `https://kadoomi.com` pour le domaine `kadoomi.com`
- [ ] Un test vérifie qu'une variable déjà présente dans Vercel n'est pas
      réécrite
- [ ] Un test vérifie que sans `generate` le défaut reste `SESSION_SECRET` et
      `CRON_SECRET`
- [ ] Une valeur générée n'apparaît dans aucun log ni retour d'API (un test
      le vérifie sur le détail de l'étape)