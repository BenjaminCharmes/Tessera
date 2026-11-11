---
agent: codeur
created: 2026-11-11
depends_on: []
estimated_days: 0.1
id: ticket-927
pr_number: null
priority: high
status: done
title: "The CI gate runs as it is on the base, and PR code gets no secret"
type: fix
---

# ticket-927 — La porte de la CI tourne telle qu'elle est sur la base, et le code d'une PR ne reçoit aucun secret

## Objectif

Qu'une PR, écrite par un agent ou non, ne puisse ni désarmer la porte des
termes interdits ni lire un secret de la CI.

## Contexte

Audit sans contexte du 11/11 :

- le job « Termes interdits (ADR-048) » de `.github/workflows/ci.yml` lançait
  `scripts/termes_interdits_ci.py` tel que la PR le livre, avec
  `FORBIDDEN_TERMS` dans son environnement : une PR qui réécrit le script
  désarmait le contrôle et pouvait lire la liste ;
- le job backend donnait `ANTHROPIC_API_KEY` (secret, s'il existe) à un
  pytest que la PR contrôle, alors que les tests qui demandent une vraie clé
  sont marqués `integration` et exclus.

Vérifié le 11/11 : aucune variable `CI_RUNNER` ni runner auto-hébergé ; la CI
tourne sur les runners GitHub.

Fait **à la main** : `.github/workflows/` est refusé à tout agent.

## Ce qui est fait

- La porte extrait `scripts/termes_interdits_ci.py` et
  `scripts/hooks/pre-push` de `BASE_SHA` dans `$RUNNER_TEMP` et les exécute
  de là. Une PR qui modifie la porte est donc jugée par l'ancienne version.
- La clé du job backend est une constante factice.

## Critères d'acceptation

- [x] `.github/workflows/ci.yml` exécute la porte depuis `BASE_SHA`.
- [x] `.github/workflows/ci.yml` ne passe plus aucun secret au job backend.
- [x] Les tests de la porte passent et la CI de la PR est verte.

## Ce que ça ne fait pas

- Ne protège pas `scripts/termes_interdits_ci.py` en écriture côté agents :
  c'est un ticket de code à part (audit du 11/11).
