---
agent: codeur
created: 2026-10-07
depends_on: []
estimated_days: 0.5
id: ticket-370
pr_number: null
priority: critical
status: done
title: A project id is validated on every route and can never point outside the projects
  folder
type: fix
---

# ticket-370 — Un identifiant de projet ne sort jamais du dossier des projets

## Objectif

Qu'aucune route ne puisse lire ou écrire hors du dossier des projets à partir
d'un `project_id` comme `..`.

## Contexte

Les routes construisent le chemin d'un projet par
`settings.ide_workspace_dir / project_id` (`ProjectLoader.load_project`,
`backend/src/tessera/services/project_loader.py`, et les routeurs de
`backend/src/tessera/routers/`), sans valider l'identifiant. Constaté le
2026-10-07 sur le backend en marche :

- `GET /api/v1/projects/../tickets` (chemin envoyé tel quel) répond 200 ;
- sous Windows, `GET /api/v1/projects/..%5C../tickets` répond 200 aussi,
  deux niveaux au-dessus du dossier des projets.

L'API n'écoute que sur 127.0.0.1, mais rien ne garantit qu'une route
d'écriture refuse ce chemin. L'audit sécurité du ticket-366 l'a relevé en
HIGH : la faiblesse est commune à toutes les routes, elle se corrige en un
seul endroit.

## Solution proposée

1. Une fonction unique, par exemple `valider_project_id` dans
   `backend/src/tessera/services/project_loader.py`, qui accepte un
   identifiant `^[A-Za-z0-9][A-Za-z0-9._-]*$` et refuse tout le reste,
   notamment `.`, `..`, les séparateurs `/` et `\`. Les identifiants actuels
   (`ide-core`, `cookie_clicker`, `habit-tracker`…) restent valides.
2. Une dépendance FastAPI appliquée au niveau des routeurs qui ont un
   paramètre de chemin `project_id` : un identifiant invalide répond 404,
   sans toucher au disque.
3. Les corps de requête qui portent un `project_id` (`RunRequest`,
   `RunAutonomousRequest` dans `backend/src/tessera/routers/orchestrator.py`)
   le valident aussi : 422 sinon.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_project_id_valide.py` vérifie que `valider_project_id` accepte `ide-core`, `cookie_clicker` et `habit-tracker`, et refuse `.`, `..`, `../x`, `..\x` et la chaîne vide
- [ ] Un test de `backend/tests/test_project_id_valide.py` parcourt toutes les routes de l'application dont le chemin contient `{project_id}` et vérifie que chacune répond 404 avec `project_id` égal à `..`
- [ ] Un test de `backend/tests/test_project_id_valide.py` vérifie que `GET /api/v1/projects/..%5C../tickets` répond 404
- [ ] Un test de `backend/tests/test_project_id_valide.py` vérifie que `POST /api/v1/orchestrator/run` avec `project_id` égal à `..` répond 422
- [ ] Un test de `backend/tests/test_project_id_valide.py` vérifie que `GET /api/v1/projects/{id}/tickets` répond toujours 200 pour un projet valide

## Dépendances

Aucune.

## Estimation

0,5 jour.

## Risques

Un projet existant dont le dossier porterait un caractère hors de la liste
deviendrait inaccessible : aucun des projets actuels n'est dans ce cas, et le
premier critère le vérifie sur leurs formes.

## Ce que ça ne fait pas

- Ne change pas l'authentification, qui est globale (`StaticTokenMiddleware`,
  `backend/src/tessera/main.py`).
- Ne valide pas les chemins de fichiers à l'intérieur d'un projet
  (`routers/fs.py` a ses propres contrôles).