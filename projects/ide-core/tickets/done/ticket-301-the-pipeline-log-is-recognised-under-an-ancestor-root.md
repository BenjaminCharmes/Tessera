---
id: ticket-301
title: "The pipeline log is recognised as bookkeeping when the project works in its parent repository"
type: fix
status: done
pr_number: null
priority: critical
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-01
---

# ticket-301 — Le journal du pipeline est reconnu sous `git_root: ancestor`

## Objectif

Qu'une file d'ide-core passe d'un ticket au suivant quand la livraison a
écrit dans le journal après son dernier commit.

## Contexte

Le 2026-10-01, la file ide-core a refusé deux fois son ticket suivant pour
cause d'arbre sale (`dirty_working_tree`) : le 283 après le 282, puis le 284
après le 283. Aucun agent n'avait tourné. Seul
`projects/ide-core/memory/pipeline-log.md` était modifié.

- Depuis le ticket-288, la livraison journalise la durée de chacune de ses
  étapes. Elle le fait après le commit de tenue de livres, donc ces lignes
  restent non commitées.
- `GitWorkspaceService.is_clean` doit ignorer ce journal (ticket-278), mais il
  compare les chemins de `git status --porcelain` à `memory/pipeline-log.md`.
  Or `--porcelain` donne les chemins depuis la racine du dépôt. Sous
  `git_root: ancestor`, c'est `projects/ide-core/memory/pipeline-log.md` :
  la tolérance du 278 n'avait donc jamais fonctionné pour ide-core. Rien ne
  journalisait après le commit avant le 288.

Fait à la main : sans ce correctif, chaque file s'arrête après son premier
ticket.

## Solution

`is_clean` retire de chaque chemin le préfixe du projet dans le dépôt
(`git rev-parse --show-prefix`) avant de le comparer aux artefacts.

## Critères d'acceptation

- [x] Un test, sur un dépôt parent contenant `projects/ide-core` en
      `git_root: ancestor`, vérifie qu'un journal modifié laisse `is_clean`
      à vrai. Il échoue sans le correctif.
- [x] Un test vérifie qu'un fichier de code modifié dans ce dépôt rend
      toujours `is_clean` faux
- [x] Les tests de `test_git_workspace.py` passent

## Ce que ça ne fait pas

`_exclude_pathspecs` et `_purger_stage_ignoré` comparent eux aussi des
chemins à `_ORCHESTRATOR_ARTIFACT_PATHS`. Le premier passe par des pathspecs
git, relatifs au dossier courant, donc corrects. Le second lit
`ls-files`, relatif lui aussi. Aucun des deux ne présente ce défaut.
