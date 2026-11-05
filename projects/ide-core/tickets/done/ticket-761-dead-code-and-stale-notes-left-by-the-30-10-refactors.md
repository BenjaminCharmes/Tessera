---
agent: codeur
created: 2026-11-03
depends_on: []
estimated_days: 1
id: ticket-761
pr_number: 909
priority: low
status: done
title: Dead code and stale notes left by the 30/10 refactors
type: chore
---

# ticket-761 — Code mort et notes périmées laissés par les refactorisations du 30/10

## Objectif

Retirer ce que les refactorisations 676-687 ont laissé derrière elles, et fixer par un test
le comportement que 676 a changé sans le dire.

## Contexte

Audit du 30/10 (relecture du 03/11).
- Méthodes `_sur_la_base` des doubles, plus appelées depuis 686 :
  `backend/tests/test_depart_depuis_la_base.py`, `backend/tests/test_git_workspace.py`,
  `backend/tests/test_ticket_bloque_livre_a_la_main.py`.
- Alias `_RUN_LOCK` inutilisé dans `backend/src/tessera/routers/orchestrator.py`.
- `backend/src/tessera/services/service_etat.py` cite `Service.en_dict()`, supprimé.
- `_racine_ancestrale` (`backend/src/tessera/services/project_overview.py`) part désormais
  du parent et accepte un fichier `.git` (worktree) : comportement voulu, non testé.

## Critères d'acceptation

- [ ] Le diff retire les trois méthodes `_sur_la_base`, l'alias `_RUN_LOCK` et la mention de
      `Service.en_dict()`
- [ ] Un test vérifie que `_racine_ancestrale` trouve un parent dont `.git` est un fichier
- [ ] Un test vérifie que, pour un projet qui porte son propre `.git` sous un parent `.git`,
      `_racine_ancestrale` rend le parent