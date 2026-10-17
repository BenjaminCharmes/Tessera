---
agent: codeur
created: 2026-10-17
depends_on: []
estimated_days: 0.5
id: ticket-499
pr_number: null
priority: high
status: done
title: Neon calls carry the organization id, so provisioning finds and creates databases
  in an organization-owned account
type: fix
---

# ticket-499 — Les appels Neon portent l'id d'organisation

## Objectif

L'étape « Base Neon » de la mise en ligne fonctionne sur un compte Neon
rattaché à une organisation, ce qui est le cas du compte de Tessera.

## Contexte

17/10, passage à blanc de la mise en ligne de Kadoomi
(`GET /api/v1/projects/kadoomi/provision`) : l'étape `database` rend
`failed — neon: HTTP 400 (unknown)`. Le corps de la réponse de Neon dit
« org_id is required, you can find it on your organization settings page ».
Le compte n'a qu'une organisation, gérée par Vercel
(`GET /users/me/organizations` → un seul élément, `managed_by: "vercel"`).
`NeonClient.find_projects` appelle `GET /projects` sans `org_id`, tout comme
`create_project` qui fait `POST /projects`.

Le message « HTTP 400 (unknown) » cache en plus la raison que Neon donne.

## Solution proposée

1. `Settings.neon_org_id` (facultatif). Absent : `NeonClient` lit
   `GET /users/me/organizations` une fois ; une seule organisation → son id ;
   aucune → appels sans `org_id` (compte personnel) ; plusieurs → l'étape rend
   `needs_human` en demandant de renseigner `NEON_ORG_ID`.
2. `org_id` est passé en paramètre de `GET /projects` et dans le corps de
   `POST /projects` (`project.org_id`).
3. Une erreur HTTP de Neon reprend le champ `message` de la réponse dans le
   détail de l'étape (jamais un en-tête ni le jeton).

## Ce que ça ne fait pas

- Ne gère pas le cas où Neon refuse la création dans une organisation gérée
  par Vercel : si l'API le refuse, l'étape rend l'erreur de Neon, lisible.
- Ne touche à aucune autre étape.

## Critères d'acceptation

- [ ] Un test vérifie que `find_projects` envoie `org_id` quand
      `neon_org_id` est réglé
- [ ] Un test vérifie que, sans réglage, une seule organisation lue sur
      `/users/me/organizations` fournit l'`org_id` des appels suivants
- [ ] Un test vérifie que plusieurs organisations sans réglage rendent
      `needs_human` avec « NEON_ORG_ID »
- [ ] Un test vérifie que `create_project` met `org_id` dans le corps
- [ ] Un test vérifie qu'un 400 de Neon donne un détail d'étape contenant le
      `message` de la réponse