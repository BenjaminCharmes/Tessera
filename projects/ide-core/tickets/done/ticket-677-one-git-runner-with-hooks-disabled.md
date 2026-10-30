---
agent: codeur
created: 2026-10-29
depends_on: []
id: ticket-677
priority: high
status: done
title: One git runner with hooks disabled
type: refactor
---

# ticket-677 — Un exécuteur `git` unique, hooks neutralisés

## Objectif
Un seul exécuteur de commandes `git` pour le backend, qui neutralise les hooks
(`-c core.hooksPath=<dossier vide>`, ADR-027) pour toute commande qui écrit.

## Contexte
Onze exécuteurs (`docs/audit/doublons.md` §1.3), trois types de retour. Trois
neutralisent les hooks (`temporary_worktree.py:21`, `reprise_orphelin.py:53`,
`socle.py:221`). `journal_en_attente.py:48` (`checkout`) et
`realignement_base.py:116` / `:129` (`fetch`, `pull --ff-only`) écrivent sans
cette protection.

## Critères d'acceptation
- [ ] Un module porte l'exécuteur ; les `_git` / `_run_git` / `run_git` de `branch_cleanup.py`, `journal_en_attente.py`, `project_removal.py`, `realignement_base.py`, `reprise_orphelin.py`, `ticket_diff.py`, `temporary_worktree.py` l'appellent
- [ ] Le type de retour est unique (code, sortie, erreur) ; aucun appelant ne décode la sortie lui-même
- [ ] Toute commande qui écrit (`checkout`, `pull`, `commit`, `merge`, `rebase`, `worktree`) passe hooks neutralisés ; un test lance une commande d'écriture dans un dépôt dont un hook écrit un fichier-témoin et constate que le témoin n'existe pas
- [ ] `test_every_git_runner_disables_hooks` : pour chaque module appelant listé au premier critère, une commande d'écriture passe par l'exécuteur commun avec les hooks neutralisés (audit de sécurité, S-17)
- [ ] Une lecture (`diff`, `status`, `rev-parse`, `log`) n'est pas ralentie par un dossier créé à chaque appel
- [ ] `uv run pytest` et `uv run mypy` passent

## Ce que ça ne fait pas
- Ne touche pas `socle.py` au-delà de l'appel à l'exécuteur commun : `git_workspace/` a ses propres contraintes de verrou
- Ne change aucune commande émise, seulement la façon de la lancer
- Ne tranche pas si `doctor.py:189` doit rester indépendant de l'application ; s'il le doit, la PR le dit