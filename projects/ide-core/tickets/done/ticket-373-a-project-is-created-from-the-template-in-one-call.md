---
agent: codeur
created: 2026-10-07
depends_on:
- ticket-372
estimated_days: 1
id: ticket-373
pr_number: null
priority: high
status: done
title: A project is created from the template in one call, with free ports and a ready
  agents.json
type: feat
---

# ticket-373 — Créer un projet depuis le gabarit en un appel

## Objectif

Un seul appel crée un projet prêt à recevoir des tickets : squelette copié,
ports libres attribués, `agents.json` prérempli, dossiers de tickets et de
mémoire, dépôt git local.

## Contexte

Monter un projet à la main demande aujourd'hui, en plus du squelette
(ticket-372) : adapter `agents.json` (`autonomy: merge`,
`merge_without_ci: true`, `base_branch: main`, une `test_command` complète en
`python -m` à cause de WDAC, les `services`), chercher des ports libres en
relisant les `agents.json` et `vite.config.ts` des autres projets, puis
`git init`.

`ProjectLoader.create_project` (`backend/src/tessera/services/project_loader.py`)
crée déjà les dossiers `tickets/` et `memory/`, un `CLAUDE.md` minimal et un
`agents.json` par défaut, et initialise le dépôt git (ticket-104,
`ProjectCreationResult.git_ready`). Les ports en usage le 2026-10-07 :
backend 8010, 8020 à 8024 ; frontend 5180, 5190 à 5194.

## Solution proposée

1. `POST /api/v1/projects/from-template` avec `{project_id, name}` :
   s'appuie sur `create_project`, puis copie `templates/fastapi-react/` dans
   le projet en remplaçant les marqueurs du ticket-372.
2. Les ports : le premier couple `(8020 + n, 5190 + n)`, n ≥ 0, dont aucun
   port n'est déjà utilisé par un projet du dossier des projets — lus dans
   les `services` des `agents.json` et dans les `vite.config.ts`.
3. L'`agents.json` écrit porte `autonomy: merge`, `merge_without_ci: true`,
   `base_branch: main`, `artifacts: tracked`, deux `services` (backend en
   `uv run python -m uvicorn app.main:app` sur le port attribué, frontend en
   `npm run dev`), et `pipeline.test_command` reprenant celle de
   habit-tracker : typecheck, lint, test, build frontend, puis
   `uv --directory backend run python -m mypy .` et
   `uv --directory backend run python -m pytest -q`.
4. Le `CLAUDE.md` créé reste le minimal actuel (titre du projet) : il s'écrit
   à la main ensuite. Aucun dépôt GitHub n'est créé.
5. La réponse rend le projet, les deux ports attribués et `git_ready`.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_projet_depuis_gabarit.py` crée un projet dans un dossier de projets temporaire et vérifie que `backend/app/main.py`, `frontend/vite.config.ts`, `tickets/todo/` et `memory/` existent, sans aucun marqueur `{{` restant
- [ ] Un test de `backend/tests/test_projet_depuis_gabarit.py` vérifie qu'avec deux projets existants utilisant 8020/5190 et 8021/5191, le nouveau projet reçoit 8022 et 5192, et que `frontend/vite.config.ts` et les `services` de son `agents.json` portent ces ports
- [ ] Un test de `backend/tests/test_projet_depuis_gabarit.py` vérifie que l'`agents.json` produit a `autonomy` égal à `merge`, `merge_without_ci` vrai, `base_branch` égal à `main`, et une `pipeline.test_command` qui contient `python -m pytest` et `python -m mypy`
- [ ] Un test de `backend/tests/test_projet_depuis_gabarit.py` vérifie que la création d'un `project_id` déjà existant répond 409 sans rien écrire
- [ ] Un test de `backend/tests/test_projet_depuis_gabarit.py` vérifie qu'aucun appel à l'API GitHub n'est fait pendant la création
- [ ] Un test de `backend/tests/test_projet_depuis_gabarit.py` vérifie que la réponse porte les deux ports attribués et `git_ready`

## Dépendances

ticket-372 (le gabarit).

## Estimation

1 jour.

## Risques

Un port libre côté Tessera peut être pris par un autre programme de la
machine : l'attribution ne regarde que les projets, comme on le faisait à la
main.

## Ce que ça ne fait pas

- Ne crée pas le dépôt GitHub et ne touche pas au jeton d'accès : étape
  séparée, sur confirmation explicite.
- N'écrit pas le `CLAUDE.md` du projet au-delà du minimal.
- Pas d'interface : ticket-374.