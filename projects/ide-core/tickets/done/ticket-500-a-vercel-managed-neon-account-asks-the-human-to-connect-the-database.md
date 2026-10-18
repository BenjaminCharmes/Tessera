---
agent: codeur
created: 2026-10-18
depends_on: []
estimated_days: 0.5
id: ticket-500
pr_number: 522
priority: high
status: done
title: When Neon refuses to create a project in a Vercel-managed organization, the
  database step asks the human to connect it from Vercel
type: fix
---

# ticket-500 — Une organisation Neon gérée par Vercel : la base se branche depuis Vercel

## Objectif

Quand la seule organisation Neon du compte est gérée par Vercel, l'étape
« Base Neon » de la mise en ligne ne finit plus en échec : elle rend
`needs_human` et dit comment brancher la base depuis Vercel.

## Contexte

18/10, mise en ligne de Kadoomi, après le ticket-499 : `GET /projects?org_id=…`
répond 200, mais `POST /projects` répond 404. L'organisation
(`GET /users/me/organizations`) porte `managed_by: "vercel"` : ses projets se
créent depuis Vercel (Storage › Neon), pas par l'API de Neon. L'étape s'arrête
en échec et bloque toute la suite (variables, Resend, DNS, déploiement).

Le ticket-499 l'avait noté comme limite (« Ne gère pas le cas où Neon refuse la
création dans une organisation gérée par Vercel »).

L'étape sait déjà sauter Neon quand `DATABASE_URL` existe dans le projet
Vercel (`_shortcut` de `neon_steps.py`).

## Solution proposée

1. `NeonClient` garde le `managed_by` de l'organisation qu'il a choisie.
2. Organisation gérée par Vercel et aucun projet Neon trouvé : `inspect` et
   `apply` rendent `needs_human`, sans `POST /projects`, avec le détail :
   « Organisation Neon gérée par Vercel : dans Vercel, projet <id> › Storage ›
   Create Database › Neon, en reliant Production et Preview. La relance lira
   DATABASE_URL. »
3. Un `POST /projects` refusé (4xx) dans les autres cas reste un échec, avec le
   message de Neon (ticket-499).

## Ce que ça ne fait pas

- Ne crée pas la base par l'API Vercel (intégration Marketplace) : piste à
  part si le cas se répète.

## Critères d'acceptation

- [ ] Un test vérifie qu'une organisation `managed_by: "vercel"` sans projet
      rend `needs_human` sans appeler `POST /projects`
- [ ] Un test vérifie que le détail nomme « Storage » et le nom du projet
- [ ] Un test vérifie qu'une organisation non gérée par Vercel crée toujours le
      projet comme avant
- [ ] Un test vérifie qu'avec `DATABASE_URL` présente dans Vercel l'étape est
      sautée, organisation gérée par Vercel ou non