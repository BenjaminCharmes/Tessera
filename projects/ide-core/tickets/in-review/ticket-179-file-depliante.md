---
id: ticket-179
title: "Une file ne montre que son ticket courant, pas ceux qui l'ont précédé"
type: feat
status: in-review
pr_number: null
priority: medium
agent: codeur
depends_on: ["ticket-172"]
estimated_days: 1
created: 2026-09-25
---

# ticket-179 — Voir toute la file, pas seulement son ticket courant

## Objectif

Qu'une file montre ce qu'elle a fait autant que ce qu'il lui reste.

## Contexte

Ticket-172 a rendu l'avancement visible — `file 2/3` — et nommé les tickets
restants. Il manque l'autre moitié : **ceux qui sont déjà passés**, et leur
issue.

Une file de quatre tickets qui affiche « 3/4 » ne dit pas si les deux premiers
ont été approuvés ou bloqués. C'est pourtant ce qu'on veut savoir avant de la
laisser finir, ou de l'arrêter : une file s'interrompt au premier ticket non
approuvé, donc voir passer un blocage change ce qu'on fait ensuite.

## Solution proposée

`RunActif` retient les tickets déjà traités, comme il retient les restants
depuis ticket-172. La carte les déplie à la demande — repliée par défaut, parce
que ce qu'elle montre sans qu'on l'ouvre se paie sur chaque carte.

## Critères d'acceptation

- [ ] `RunActif` porte les tickets déjà traités, et `en_dict` les publie
- [ ] Un run hors file les laisse vides
- [ ] La liste est repliée par défaut et se déplie à la demande
- [ ] Elle montre les tickets faits **et** les restants, dans l'ordre de la file
- [ ] Un run unique n'affiche aucune liste
- [ ] `uv run pytest`, `npx vitest run`, `tsc`, `eslint` et `npm run build`
      passent

## Dépendances

ticket-172, dont il complète le mécanisme.

## Estimation

Moins d'une journée.

## Risques

Une carte qui grossit. Bornée par le repli : l'état par défaut ne change pas.
