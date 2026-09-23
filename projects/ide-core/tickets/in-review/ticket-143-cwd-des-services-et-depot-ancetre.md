---
id: ticket-143
title: "Le cwd d'un service doit honorer git_root: ancestor"
type: fix
status: in-review
pr_number: null
priority: medium
agent: codeur
depends_on: ["ticket-137"]
estimated_days: 1
created: 2026-09-23
---

# ticket-143 — Le `cwd` d'un service et le dépôt ancêtre

## Objectif

Rendre `ide-core` lançable depuis l'IDE, sans ouvrir le périmètre des autres
projets.

## Contexte

ticket-137 refuse un `cwd` qui sort de la racine du projet — même frontière
qu'ADR-031, et pour la même raison : six dépôts clients côte à côte dans
`projects/`, un `cwd` mal écrit démarre un serveur dans le mauvais.

Mais ce contrôle ignore l'exception d'**ADR-028**. Le projet bootstrap
travaille volontairement dans le dépôt qui le contient — son code est dans
`../../backend/` et `../../frontend/` — et il le déclare par
`"git_root": "ancestor"`. Conséquence : `ide-core` ne peut pas déclarer ses
propres services, alors que c'est le projet qui construit l'IDE.

Le trou vient d'avoir réécrit une règle qui existait : `perimetre.py` porte
déjà `racine_autorisee(project_path)`, qui rend le dossier du projet ou le
dépôt ancêtre selon ce que le manifeste déclare. `process_registry` compare à
la racine du projet, en dur.

## Solution proposée

`resoudre_le_cwd` s'appuie sur `racine_autorisee()` au lieu de comparer à la
racine du projet. Une règle, une description (ADR-034) : deux contrôles de
périmètre finiraient par diverger, et c'est celui qu'on regarde le moins qui
laisserait passer.

Ce que ça ne change pas : un projet qui ne déclare rien reste enfermé dans son
dossier, et seule la valeur exacte `ancestor` élargit le périmètre.

## Critères d'acceptation

- [ ] Un test vérifie qu'un projet **sans** `git_root` refuse toujours un
      `cwd` qui sort de son dossier
- [ ] Un test vérifie qu'un projet déclarant `git_root: ancestor` accepte un
      `cwd` situé dans le dépôt qui le contient
- [ ] Un test vérifie qu'une valeur inconnue de `git_root` ne désarme rien
- [ ] `resoudre_le_cwd` n'implémente plus sa propre résolution de racine
- [ ] `ide-core` peut déclarer ses services et les lancer
- [ ] `uv run pytest` et `uv run mypy src/` passent

## Dépendances

ticket-137.

## Estimation

1 jour.

## Risques

Élargir un périmètre est le geste qui se relit le moins bien : le test sur la
valeur inconnue est ce qui garantit que l'exception reste une exception.
