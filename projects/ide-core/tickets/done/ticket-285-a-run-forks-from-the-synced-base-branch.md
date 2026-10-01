---
agent: codeur
created: 2026-10-01
depends_on: []
estimated_days: 1
id: ticket-285
plan: true
pr_number: null
priority: critical
status: done
title: A run forks from its base branch synced with the remote, not from whatever
  HEAD is checked out
type: fix
---

# ticket-285 — Un run part de sa base à jour, pas du HEAD du moment

## Objectif

Que le premier ticket d'un run parte de `base_branch` alignée sur le distant,
et que la livraison rebase sur cette même base à jour : une PR ne doit
contenir que les commits de son ticket.

## Contexte

Constaté sur `freelance` le 2026-10-01. Après un run livré, le dépôt reste sur
la branche du ticket. Le 2026-09-30, le ticket-012 a été mergé en squash (#8),
et le dépôt est resté sur `ticket-012-…`, avec un `main` local en retard.

Le lendemain, une file a démarré :

- `GitWorkspaceService.create_branch` prend `_base_ref = rev-parse HEAD` au
  premier appel (`services/git_workspace.py:283-284`), donc la pointe de
  `ticket-012-…`. Le ticket-006 a forké de là.
- La livraison rebase sur `base_branch` **locale**
  (`services/livraison.py:151-153`, `rejouer_sur(self._base_branch)`), donc sur
  le `main` périmé, qui ne contient pas le squash #8.
- La PR #9 a embarqué les deux commits du 012, déjà mergés : `CONFLICTING`,
  merge automatique jamais fait, et le ticket-007 empilé sur la même base.

`sync_base_depuis_distant` (ticket-264, `git_workspace.py:313`) sait déjà
aligner la base locale sur le distant, mais il ne sert qu'**entre** deux
tickets d'une file, après un merge. Tessera lui-même a été trouvé le même jour
sur la branche du ticket-278 : seul le hasard d'un `develop` à jour a évité le
même défaut.

## Solution proposée

- Au premier `create_branch` d'un run, la base est `base_branch`, d'abord
  alignée sur le distant par `sync_base_depuis_distant`, et non `HEAD`. Sans
  distant joignable, la base est `base_branch` locale. Si elle n'existe pas
  non plus, c'est `HEAD`, comme aujourd'hui.
- Une base locale qui a divergé du distant n'est pas écrasée : le run s'arrête
  en `blocked` avec la raison que rend déjà `sync_base_depuis_isant`.
- Avant `rejouer_sur`, la livraison aligne la base sur le distant, pour
  rebaser sur l'état réel de la branche cible.
- Le tour de plan vérifie comment `base_branch` atteint `GitWorkspaceService`,
  pour le projet bootstrap (`git_root: ancestor`, base `develop`) comme pour
  un dépôt tiers.

## Critères d'acceptation

- [x] Un test sur un vrai dépôt git temporaire, avec un distant nu, vérifie
      qu'un run démarré alors que `HEAD` est sur une ancienne branche de
      ticket crée sa branche depuis `origin/<base_branch>`
- [x] Un test vérifie que, sans distant, la branche est créée depuis
      `base_branch` locale et non depuis `HEAD`
- [x] Un test vérifie qu'une base locale divergente arrête le run en `blocked`
      avec une raison qui nomme la branche, sans réécrire la base
- [x] Un test vérifie que la livraison aligne la base sur le distant avant
      `rejoyer_sur`
- [x] Un test reproduit le cas de `freelance` (ticket A mergé en squash,
      dépôt laissé sur la branche de A, puis ticket B) et vérifie que les
      commits de B depuis la base ne contiennent aucun commit de A

## Ce que ça ne fait pas

Le dépôt n'est pas remis sur `base_branch` après livraison : une fois que la
base ne dépend plus de `HEAD`, rester sur la branche du ticket ne coûte rien.

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Le projet bootstrap travaille dans le dépôt de Tessera : un `fetch` y touche
les refs du dépôt que le développeur utilise aussi, mais `sync_base_depuis_distant`
ne fait qu'un fast-forward, et refuse sinon.