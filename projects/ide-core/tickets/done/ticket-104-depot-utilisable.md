---
id: ticket-104
title: "Un projet créé part avec un dépôt utilisable"
type: feat
status: done
pr_number: 102
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-21
---

# ticket-104 — Un projet créé part avec un dépôt utilisable

## Objectif

Qu'un projet créé depuis l'IDE soit la racine de son propre dépôt git, donc
qu'un premier run de pipeline y fonctionne sans intervention manuelle.

## Contexte

`ProjectLoader.create_project` crée les dossiers et le `CLAUDE.md`, mais ne
fait **aucun `git init`**.

Sans dépôt à la racine du projet, `GitWorkspaceService` lève
`NotAGitRepository` : ADR-024 exige que `git rev-parse --show-toplevel` renvoie
exactement le dossier du projet, précisément pour qu'un projet posé dans
`projects/` ne fasse pas remonter git jusqu'au dépôt de Tessera. Le run
s'arrête donc **avant la première branche**, et rien n'est commité.

Autrement dit : tout projet créé depuis l'UI est né inutilisable pour le
pipeline, et l'utilisateur ne l'apprend qu'au premier run, sous la forme d'une
erreur qui ne dit pas quoi faire.

## Solution proposée

1. Après la création, initialiser le dépôt dans `POST /api/v1/projects`.
2. Réutiliser `init_repository()` de `services/git_link.py` — il n'initialise
   que si `.git` est absent, et fait le commit initial. Ne pas réécrire un
   `git init`.
3. L'appeler **après** `apply_artifact_mode(...)`. Dans l'autre ordre, le
   commit initial versionnerait les artefacts que le mode devait exclure
   (ADR-021, ADR-023).
4. Un échec de git ne fait **pas** échouer la création : le projet existe déjà
   sur disque, et rendre une erreur laisserait l'utilisateur avec un projet
   créé et un message d'échec. L'état part dans la réponse, comme
   `agents_created` le fait déjà.
5. L'UI dit ce qui s'est passé, et renvoie vers `GitLinkPanel` si l'init a
   échoué — c'est de là qu'on rattrape à la main.

Ce ticket **ne touche pas** à `CLAUDE.md`.

## Critères d'acceptation

- [ ] Un projet créé par `POST /api/v1/projects` contient un `.git` à sa racine
- [ ] `git rev-parse --show-toplevel` y renvoie le dossier du projet lui-même
- [ ] Le dépôt porte un commit initial, donc `git status --porcelain` est vide
- [ ] `ProjectCreationResult` porte l'état du dépôt, et un test vérifie qu'il
      est vrai sur un projet créé normalement
- [ ] Un `init_repository` qui lève rend malgré tout un **201**, avec l'état à
      faux — jamais un 500
- [ ] L'initialisation a lieu **après** `apply_artifact_mode` : un test vérifie
      qu'un projet en mode `local` n'a pas ses artefacts dans le commit initial
- [ ] L'UI de création affiche l'état du dépôt
- [ ] `.\scripts\tessera.ps1 verify` est vert de bout en bout

## Dépendances

Aucune. Le ticket-105 touche le même fichier et part de `develop` après
celui-ci.

## Estimation

1 jour.

## Risques

`init_repository` fait un `git add -A` avant son commit initial. C'est sûr ici
parce que le mode des artefacts est posé avant, et que la fonction le
réapplique elle-même après `git init` — `.git/info/exclude` n'existant pas
auparavant. Inverser les deux appels réintroduirait la fuite d'ADR-021.
