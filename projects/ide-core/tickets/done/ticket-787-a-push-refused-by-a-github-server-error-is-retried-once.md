---
id: ticket-787
title: "A push refused by a GitHub server error is retried once"
type: fix
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-04
---

# ticket-787 — Un push refusé par une erreur serveur de GitHub est retenté une fois

## Objectif

Une livraison approuvée ne s'arrête plus sur une seule erreur serveur passagère de GitHub au
push.

## Contexte

04/11 : plusieurs erreurs 500 passagères de GitHub (incident en cours). File portfolio
159ff03b : le push de ticket-021 échoue (« remote: fatal error in commit_refs », 500) et la
livraison s'arrête ; un nouvel essai à la main, un peu plus tard, passe. Côté ide-core, des
push à la main ont aussi reçu `Internal Server Error` puis sont passés au deuxième essai.

`push_branch` (`backend/src/tessera/services/git_workspace/poussee.py`) ne rejoue un push que
pour une course perdue (`cannot lock ref`, ticket-539). Le ticket-781 traite l'ouverture de la
PR, pas le push.

## Solution proposée

- Sur un refus dont la sortie d'erreur signale une erreur serveur (`Internal Server Error`,
  `HTTP 5xx`, `fatal error in commit_refs`, `502 Bad Gateway`…), relire le distant : à jour,
  le push a réussi ; sinon attendre un court délai et rejouer le push **une** fois, sans force
  (ADR-022).
- Tout autre refus remonte comme aujourd'hui.

## Critères d'acceptation

- [x] Un test vérifie, avec un exécuteur git double, qu'un push refusé avec
      « Internal Server Error » puis accepté réussit en deux appels
- [x] Un test vérifie que deux refus serveur de suite font remonter l'erreur, en deux appels
- [x] Un test vérifie qu'un refus `non-fast-forward` n'est pas rejoué
- [x] Un test vérifie qu'aucun appel ne porte `--force` ni `--force-with-lease`
