---
id: ticket-488
title: "Putting a project online runs its Resend and Stripe steps, and a Vercel repo_not_found says what to install"
type: fix
status: todo
pr_number: null
priority: critical
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-16
---

# ticket-488 — La mise en ligne lance aussi Resend et Stripe

## Objectif

`POST /api/v1/projects/{id}/provision` exécute toutes les étapes que le bloc
`online` déclare, Resend et Stripe compris, et un refus de Vercel faute
d'accès au dépôt dit quoi faire.

## Contexte

16/10, première mise en ligne réelle (devinoo, `resources: vercel, database,
resend, dns, stripe`) : la réponse ne liste que `vercel_project, database,
variables, dns, redeploy`. `build_setup` dans
`backend/src/tessera/services/provisioning/launcher.py` (ticket-471) a été
écrit avant que `ResendDomainStep`, `ResendVerifyStep`
(`resend_steps.py`, ticket-468) et `StripeStep` (`stripe_step.py`,
ticket-470) soient mergés : il ne les crée jamais.

Même essai : `POST /v11/projects` renvoie 400 `repo_not_found` parce que
l'application GitHub de Vercel n'a pas accès au dépôt privé. L'étape reste
`todo` avec « Vercel project is missing », sans dire pourquoi.

## Solution proposée

1. Dans `build_setup`, l'ordre devient : projet Vercel, base, variables,
   domaine Resend (si `resend`), Stripe (si `stripe`), DNS, vérification
   Resend (si `resend`), redéploiement. Les clients viennent de
   `ResendClient.from_settings` et `StripeClient.from_settings`, comme les
   autres.
2. Dans `VercelProjectStep`, une erreur `repo_not_found` à la création rend
   l'étape `needs_human` avec : « Vercel n'a pas accès au dépôt <owner/repo> :
   installe l'application GitHub de Vercel (github.com/apps/vercel) sur ce
   dépôt, puis relance ».

## Critères d'acceptation

- [ ] Un test de `backend/tests/` vérifie que `build_setup` pour
      `resources: ["vercel", "database", "resend", "dns", "stripe"]` produit
      les étapes dans l'ordre ci-dessus
- [ ] Un test vérifie que sans `resend` ni `stripe`, ces étapes sont absentes
- [ ] Un test vérifie qu'une réponse 400 `repo_not_found` de Vercel rend
      `needs_human` avec « github.com/apps/vercel » dans le détail
- [ ] Les tests existants de `backend/tests/` sur `launcher.py` restent verts
