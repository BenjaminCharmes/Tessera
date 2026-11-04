---
agent: codeur
created: 2026-11-03
depends_on: []
estimated_days: 1
id: ticket-760
pr_number: 884
priority: medium
status: done
title: Every git write goes through the shared runner, symbolic-ref included
type: fix
---

# ticket-760 — Toute écriture git passe par l'exécuteur commun, `symbolic-ref` compris

## Objectif

Aucune écriture git de Tessera ne déclenche les hooks de l'utilisateur.

## Contexte

Audit du 30/10 (relecture du 03/11), ticket-677.
- `git_link.init_repository` (`backend/src/tessera/services/git_link.py`) fait `add -A` puis
  `commit` par son propre `_run`, sans neutraliser les hooks : un `init.templateDir`
  utilisateur (framework pre-commit) s'exécute au premier commit d'un projet importé.
- `git_runner._READS` (`backend/src/tessera/services/git_runner.py`) classe `symbolic-ref`
  en lecture ; avec deux arguments, il écrit une référence.

## Critères d'acceptation

- [ ] Un test vérifie que `writes(("symbolic-ref", "HEAD", "refs/heads/x"))` est vrai et
      `writes(("symbolic-ref", "--short", "HEAD"))` faux
- [ ] Un test vérifie qu'avec un `init.templateDir` portant un hook `pre-commit` témoin,
      `init_repository` ne produit aucun témoin
- [ ] `git_link.py` n'appelle plus `create_subprocess_exec` pour git