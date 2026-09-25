---
id: ticket-172
title: "La Supervision ne dit pas où en est une file"
type: fix
status: in-review
pr_number: null
priority: medium
agent: codeur
depends_on: ["ticket-163"]
estimated_days: 1
created: 2026-09-25
---

# ticket-172 — Une file, vue de la Supervision, n'a pas d'avancement

## Objectif

Qu'une file lancée montre où elle en est, et ce qu'il lui reste.

## Contexte

Deux files de trois tickets lancées, et la même remarque les deux fois : la
Supervision ne montre pas les tickets en attente. Sa carte affiche le projet,
le ticket courant, l'étiquette « file » — et rien qui dise qu'il y en a deux
autres derrière.

Ce n'est pas un oubli d'affichage : une file est **un** run (ADR-041), donc
une carte. L'information existe côté vue du run — son en-tête annonce
« File : 1/3 » — mais `RunActif` ne la porte pas, donc la Supervision ne peut
pas la rendre. Et depuis ticket-163, c'est l'instantané qui sème l'état d'un
observateur arrivé en cours de route : sans le champ, il ne la verra jamais
non plus.

Conséquence pratique : on ne sait pas, en regardant la Supervision, si une
file est à son premier ticket ou à son dernier — ni lesquels restent à faire
si on décide de l'arrêter.

## Solution proposée

Même forme que ticket-163 pour la question en attente : `RunActif` retient
l'avancement de la file, `en_dict` le publie, et la carte le rend.

## Critères d'acceptation

- [ ] `RunActif` porte l'index et le total de la file, et les tickets restants
- [ ] `en_dict` les publie ; un run hors file les laisse vides
- [ ] Un `queue_progress` met l'avancement à jour
- [ ] La carte d'une file affiche son avancement, celle d'un run unique non
- [ ] La carte nomme les tickets qui restent
- [ ] `uv run pytest`, `npx vitest run`, `tsc` et `eslint` passent

## Dépendances

ticket-163, dont ce ticket reprend le mécanisme.

## Estimation

Moins d'une journée.

## Risques

Une carte plus chargée. Borné : l'avancement tient en trois caractères, et la
liste des restants ne s'affiche que sur la carte sélectionnée.
