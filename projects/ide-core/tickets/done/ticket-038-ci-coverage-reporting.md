---
id: ticket-038
title: "CI — rapport de coverage automatique sur les PRs"
type: chore
status: todo
pr_number: null
priority: low
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-07-11
---

# ticket-038 — Rapport de coverage automatique sur les PRs

## Objectif

Afficher automatiquement le coverage (backend + frontend) directement sur la PR
GitHub à chaque run de CI, sans intervention manuelle. Aujourd'hui `ci.yml` calcule
déjà le coverage (`pytest --cov`, `npm run test:coverage`) mais se contente
d'uploader les rapports en artifacts — il faut télécharger et ouvrir le zip pour
voir le chiffre.

## Contexte

Le coverage est actuellement rapporté "à la main" dans les descriptions de PR.
Ce n'est pas fiable ni systématique. On veut un signal automatique, visible
directement sur la PR (commentaire et/ou check), pour chaque changement.

## Solution proposée

Ajouter une étape dans les jobs `backend` et `frontend` de `.github/workflows/ci.yml`
qui poste un résumé de coverage en commentaire sur la PR à partir de
`backend/coverage.xml` et `frontend/coverage/lcov.info`.

Deux options à trancher au moment de l'implémentation (pas de service externe
requis a priori) :

1. **Action GitHub-native** (ex. `orgoro/coverage` pour Python, ou équivalent
   lcov pour le frontend) — poste un commentaire de résumé + diff de coverage
   directement depuis le job CI, zéro compte tiers.
2. **Codecov** — plus riche (badges, historique, diff coverage détaillé par
   fichier) mais nécessite un compte externe et l'upload de `CODECOV_TOKEN`
   dans les secrets du repo.

Privilégier l'option 1 par défaut (pas de dépendance externe) sauf si on veut
l'historique/les badges de l'option 2.

## Critères d'acceptation

- [ ] Une PR modifiant du code backend et/ou frontend affiche automatiquement
      le % de coverage (global + diff) en commentaire ou en check sur la PR
- [ ] Aucune action manuelle requise — le résumé apparaît à chaque run de CI
- [ ] Le comportement existant (upload des artifacts complets) est conservé
- [ ] La CI reste verte sur un repo sans secret supplémentaire configuré
      (si Codecov est choisi, prévoir un fallback qui ne fait pas échouer le job)

## Dépendances

Aucune.

## Estimation

**0.5j** — Ajout d'une étape CI + réglage du format d'affichage, pas de code
applicatif.

## Risques

- **Faible** — Si Codecov est choisi, dépendance à un service tiers et à un
  token secret à configurer manuellement dans les settings GitHub du repo.
