---
agent: codeur
created: 2026-10-30
depends_on: []
estimated_days: 0.5
id: ticket-706
pr_number: null
priority: high
status: done
title: Tessera's .env and sibling project manifests are refused in writing
type: fix
---

# ticket-706 — Le `.env` de Tessera et les manifestes voisins se refusent en écriture (C-04)

## Objectif
Un run d'un projet `git_root: ancestor` ne doit réécrire ni le `.env` de
Tessera, ni le `agents.json` d'un autre projet, ni le hook `pre-push` du dépôt.

## Contexte
Audit de sécurité, `docs/audit/securite.md`, constats S-07 et S-08.
`motif_de_protection` (`backend/src/tessera/services/providers/chemins_proteges.py`)
ne protège que `project_path/agents.json` et ne nomme pas `.env`. Sous
`ancestor`, la racine d'écriture est le dépôt entier. Un run ide-core peut donc :
- vider `FORBIDDEN_TERMS` dans le `.env` ;
- passer un projet voisin en `autonomy: merge` ou en
  `confidentiality: professional` ;
- réécrire `scripts/hooks/pre-push`, l'une des portes d'ADR-050.

Le garde-jetons (`garde_jetons.py`) ne refuse que des lectures. Il trouve le
chemin du `.env` par `Settings.env_file`.

## Solution proposée
Dans `motif_de_protection`, refuser :
- le fichier `Settings.env_file`, une fois résolu ;
- tout `agents.json` dont le dossier parent contient un `CLAUDE.md` (c'est-à-dire
  un projet), y compris hors de `project_path` ;
- `scripts/hooks/` sous la racine.

Comme pour les motifs existants, le message de refus dit pourquoi.

## Critères d'acceptation
- [ ] `test_write_to_the_tessera_env_is_refused_under_ancestor` (dans `backend/tests/test_chemins_proteges.py`) : un `Write` et une redirection Bash vers le `.env` de `Settings.env_file` sont refusés
- [ ] `test_a_sibling_project_manifest_is_refused_under_ancestor` : `projects/autre/agents.json`, dont le dossier porte un `CLAUDE.md`, est refusé
- [ ] `test_the_pre_push_hook_script_is_refused` : `scripts/hooks/pre-push` est refusé
- [ ] `test_project_own_env_and_fixtures_still_pass` : le `.env` propre au projet, `.env.example` et `tests/fixtures/agents.json` (sans `CLAUDE.md` à côté) passent

## Ce que ça ne fait pas
- Ne touche pas aux lectures : celle du `.env` est déjà refusée (ADR-053)
- Ne couvre pas les formes de redirection collées (C-06, plus tard)