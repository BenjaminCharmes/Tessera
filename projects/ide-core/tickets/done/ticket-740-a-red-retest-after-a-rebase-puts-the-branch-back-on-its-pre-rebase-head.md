---
agent: codeur
created: 2026-11-03
depends_on: []
estimated_days: 1
id: ticket-740
pr_number: null
priority: high
status: done
title: A red retest after a rebase puts the branch back on its pre-rebase head
type: fix
---

# ticket-740 — Un retest rouge après rebase remet la branche sur sa tête d'avant

## Objectif

Une livraison arrêtée par des tests rouges après rebase ne laisse jamais la branche
locale rebasée : elle revient sur la tête qu'elle avait avant le rebase.

## Contexte

03/11, ticket-733 : à la livraison, le rebase sur `develop` entre en conflit avec le
ticket-739 ; `resolveur-conflit` résout, mais sa résolution efface la reprise réseau
de 739. Les tests relancés sont rouges : rien n'est poussé, c'est le comportement
voulu (ticket-568). Mais la branche locale **reste rebasée**, avec cette résolution
fausse et sans marqueur de conflit. Repris à la main, un `git rebase` « réussit »
sans conflit et réintroduit la régression : il a fallu lire le parent du commit pour
comprendre.

`_retester` (`backend/src/tessera/services/livraison.py`) rend l'arrêt sans toucher
la branche. La restauration existe déjà pour un rebase annulé :
`_restaurer_depuis_sha` (`backend/src/tessera/services/git_workspace/rebase.py`).

## Solution proposée

- Noter la tête de la branche juste avant `_rebaser`.
- Sur un retest rouge, remettre la branche sur cette tête (une méthode publique du
  workspace qui s'appuie sur la restauration existante), puis rendre l'arrêt.
- L'étape du journal le dit : branche remise sur `<sha court>`, résolution de
  conflit abandonnée quand il y en a eu une.
- Remise impossible : l'arrêt le dit aussi ; rien n'est poussé dans tous les cas.

## Critères d'acceptation

- [ ] Un test vérifie, avec des doubles, qu'un retest rouge après rebase remet la
      branche sur la tête notée avant le rebase
- [ ] Un test vérifie qu'un retest vert ne remet rien en place
- [ ] Un test vérifie que l'étape journalisée d'un retest rouge contient « branche
      remise sur » suivi du SHA court d'avant le rebase
- [ ] Un test vérifie qu'une remise qui lève laisse un arrêt qui le dit, sans push

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

- La tête d'avant porte les commits de rangement du pipeline : ils sont gardés, c'est
  l'état approuvé (ADR-039).