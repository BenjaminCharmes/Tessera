---
id: ticket-409
title: "A project created from the template starts on its declared base branch, ignores its build output, and describes its real agents and stack"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-13
---

# ticket-409 — Un projet issu du gabarit est cohérent avec son propre manifeste

## Objectif

Qu'un projet créé par `POST /api/v1/projects/from-template` soit prêt pour
le pipeline sans retouche : bonne branche, pas d'artefacts suivis, un
`CLAUDE.md` qui dit vrai.

## Contexte

Création de `curio` le 2026-10-13 (ticket-373 pour le gabarit). Trois
défauts, corrigés à la main sur ce projet :

1. **Branche** : `init_repository` (`services/git_link.py`) fait un
   `git init` nu ; sur une machine où `init.defaultBranch` vaut `master`,
   le dépôt naît sur `master` alors qu'`agents.json` déclare
   `base_branch: main`. Le premier run part d'une base inexistante.
2. **Pas de `.gitignore`** : `templates/fastapi-react/` n'en contient pas.
   Après `npm install` et `uv sync`, `node_modules/`, `.venv/`,
   `__pycache__/` et `frontend/dist/` apparaissent comme non suivis, prêts à
   être emportés par un commit.
3. **`CLAUDE.md` faux** : `ProjectLoader.create_project`
   (`services/project_loader.py`) écrit « _Aucun agent configuré._ » et
   « Stack : À définir. », puis `project_from_template.py` écrit un
   `agents.json` à sept rôles sans retoucher ce `CLAUDE.md`. Chaque agent lit
   donc un projet sans agents ni stack.

## Solution proposée

- `init_repository` accepte une branche initiale ; `project_from_template.py`
  lui passe `main` (la valeur qu'il écrit dans `base_branch`), via
  `git init -b <branche>`.
- Ajouter `templates/fastapi-react/.gitignore` : `node_modules/`,
  `frontend/dist/`, `.venv/`, `__pycache__/`, `.pytest_cache/`,
  `.mypy_cache/`, `*.db`, `.env`. Vérifier que `_copy_template` copie les
  fichiers commençant par un point.
- Après l'écriture d'`agents.json`, `project_from_template.py` réécrit le
  `CLAUDE.md` : section « Agents actifs » listant les rôles actifs du
  manifeste, section « Stack » nommant FastAPI + SQLite (backend) et
  React 19 + Vite + Tailwind v4 (frontend) avec les deux ports attribués.

## Critères d'acceptation

- [ ] Un test de `project_from_template` vérifie que le dépôt créé est sur la
      branche `main` même quand `init.defaultBranch` vaut `master` (variable
      `GIT_CONFIG_GLOBAL` pointée sur un fichier temporaire)
- [ ] `templates/fastapi-react/.gitignore` existe avec les huit entrées
      listées, et un test vérifie qu'il est présent dans le projet créé
- [ ] Un test vérifie que le `CLAUDE.md` du projet créé liste chaque rôle
      actif de son `agents.json` et ne contient plus « Aucun agent configuré »
      ni « À définir »
- [ ] Un test vérifie que le `CLAUDE.md` du projet créé cite ses ports
      backend et frontend

## Dépendances

Aucune.

## Risques

- `init_repository` sert aussi aux projets importés et créés sans gabarit :
  la branche reste optionnelle, le comportement par défaut inchangé.

## Ce que ça ne fait pas

- Les dépendances de développement du gabarit (vitest 3, signalé par
  `npm audit`) : un ticket à part, la montée de version étant cassante.
- La création du dépôt GitHub et l'accès du jeton : toujours manuels.
