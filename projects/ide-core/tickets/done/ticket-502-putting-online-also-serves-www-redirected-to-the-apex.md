---
agent: codeur
created: 2026-10-18
depends_on: []
estimated_days: 0.5
id: ticket-502
pr_number: 527
priority: medium
status: done
title: Putting a project online also serves www, redirected to the apex domain
type: feat
---

# ticket-502 — La mise en ligne sert aussi www, redirigé vers le domaine nu

## Objectif

Après une mise en ligne, `https://www.<domaine>` répond et redirige vers
`https://<domaine>`, sans geste à la main.

## Contexte

18/10, Kadoomi en ligne : `kadoomi.com` répond, mais `www.kadoomi.com` n'a
aucun enregistrement DNS (NXDOMAIN). L'étape `vercel_project` n'ajoute au
projet Vercel que le domaine déclaré (`VercelClient.add_domain`,
`POST /v10/projects/{id}/domains`) et l'étape DNS ne publie que ce que les
autres étapes demandent (`ctx.wanted_dns`). Beaucoup de visiteurs tapent
« www » : la page ne s'ouvre pas pour eux. Signalé par la session Kadoomi.

## Solution proposée

1. `vercel_project` ajoute aussi `www.<domaine>` au projet, avec
   `redirect: "<domaine>"` et `redirectStatusCode: 308`, s'il n'y est pas.
   Un domaine déclaré qui commence déjà par `www.` n'ajoute rien.
2. La recommandation DNS de Vercel pour `www` (`GET /v6/domains/www.<domaine>/config`,
   CNAME en général) est ajoutée à `ctx.wanted_dns`, comme pour l'apex.
3. `www` présent avec une autre cible : rien n'est écrasé, l'étape le signale
   (règle existante de l'étape DNS).

## Ce que ça ne fait pas

- Ne gère pas d'autres sous-domaines.

## Critères d'acceptation

- [ ] Un test vérifie que l'ajout du domaine `example.com` ajoute aussi
      `www.example.com` avec une redirection 308 vers `example.com`
- [ ] Un test vérifie que l'enregistrement recommandé pour `www` rejoint
      `wanted_dns`
- [ ] Un test vérifie qu'un `www.example.com` déjà présent n'est ni recréé ni
      modifié
- [ ] Un test vérifie qu'un domaine déclaré `www.example.com` n'ajoute pas de
      `www.www.example.com`