---
id: ticket-304
title: "A verification script runs pytest, mypy and the frontend checks, so the testeur catches what CI catches"
type: chore
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-10-02
---

# ticket-304 — Le testeur attrape ce que la CI attrape

## Objectif

Qu'un ticket approuvé n'échoue plus en CI sur une erreur `mypy`, `tsc` ou
`eslint` que personne dans le pipeline n'a vue.

## Contexte

Le testeur d'ide-core lance `pytest -x` sur `backend/` (ticket-295).
`test_command` n'est qu'une commande, sans shell, donc il ne peut pas
enchaîner autre chose. Le 2026-10-01, trois tickets approuvés ont pourtant
échoué en CI après l'approbation :

- 285 : une erreur `mypy` (variable réassignée à `None`) ;
- 281 : une erreur `eslint` (`setState` synchrone dans un effet), puis le
  test de cohérence visuelle ;
- 293 : une erreur `mypy` (`plugins` typé `list[dict]`).

Ni le reviewer ni le validateur ne lancent ces outils. Chaque échec a coûté
une PR rouge, une correction à la main, et souvent les tickets suivants de
la file, qui s'étaient empilés dessus.

## Solution proposée

- Un script `scripts/verifier.py`, lancé par `uv run python
  ../scripts/verifier.py` depuis `backend/`. Il enchaîne, en s'arrêtant au
  premier échec :
  1. `python -m pytest -q -x -m "not integration"` dans `backend/` ;
  2. `python -m mypy src/` dans `backend/` ;
  3. `npx tsc -b`, `npx eslint .` et `npx vitest run` dans `frontend/`.
- Sa sortie nomme l'étape qui a échoué, suivie de la sortie de l'outil, pour
  que le codeur reçoive l'erreur elle-même (`_extract_errors`).
- Chaque outil est lancé par `python -m` ou par `npx`, jamais par un lanceur
  `.exe` de `.venv` : le contrôle d'applications Windows les refuse (os
  error 4551).
- Le passage de `test_command` à ce script dans `projects/ide-core/agents.json`
  se fait **à la main** après le merge : aucun agent ne peut écrire ce
  fichier (ADR-027).

## Critères d'acceptation

- [ ] `scripts/verifier.py` existe, et un test vérifie qu'il exécute les
      étapes dans l'ordre et s'arrête à la première qui échoue (commandes
      remplacées par des doublures)
- [ ] Un test vérifie que la sortie d'un échec commence par le nom de
      l'étape, par exemple `mypy :`
- [ ] Un test vérifie que le script rend un code de sortie non nul quand
      une étape échoue, et nul quand toutes passent
- [ ] Un test vérifie qu'aucune commande du script n'appelle un exécutable
      sous `.venv`

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

La vérification passe d'environ 3 min 30 à environ 6 minutes par tour.
L'option `-x` et l'arrêt au premier échec gardent court le cas qui compte :
celui où quelque chose est cassé.
