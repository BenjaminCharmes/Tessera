---
id: ticket-773
title: "Ruff lints the backend in the test command and the CI"
type: chore
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-03
---

# ticket-773 — Ruff contrôle le backend dans la commande de test

## Objectif

Le backend Python a un linter, comme le frontend a ESLint.

## Contexte

Un comparatif externe du 03/11 relève que Tessera a mypy strict mais « aucun linter ni
formateur Python ». `backend/pyproject.toml` n'a ni `ruff`, ni `black`, ni `flake8`.

## Solution proposée

- `ruff` en dépendance `dev` de `backend/pyproject.toml`, avec une section `[tool.ruff]` :
  règles `E`, `F`, `I` (imports triés), `B`, `UP`, cible `py311`, longueur de ligne actuelle
  du code.
- Le code existant est corrigé pour passer (`ruff check --fix` puis corrections à la main) ;
  les exceptions inévitables sont nommées par fichier dans `[tool.ruff.lint.per-file-ignores]`.
- `scripts/verifier.py` lancera `ruff check` dans la chaîne backend : ce script se refuse en
  écriture à tout agent (`contraintes.md`), l'étape s'ajoute **à la main après le merge**.
- Le formateur (`ruff format`) n'est **pas** appliqué par ce ticket : il réécrirait tout le
  backend ; il fera l'objet d'un ticket séparé si on le veut.

## Critères d'acceptation

- [ ] `backend/pyproject.toml` déclare `ruff` en `dev` et une section `[tool.ruff]`
- [ ] `uv run ruff check src tests` passe depuis `backend/` (une étape du diff ou un test le
      prouve, par exemple un test qui lance ruff sur le dépôt)
- [ ] Le diff ne modifie pas `scripts/verifier.py` (ajout manuel après le merge)

## Risques

Ce ticket touche `[tool.*]` de `backend/pyproject.toml`, que la porte de configuration des
tests signale : c'est voulu, le fichier est nommé ici.
