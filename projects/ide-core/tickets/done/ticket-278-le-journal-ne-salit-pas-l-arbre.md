---
agent: codeur
created: 2026-10-01
depends_on: []
estimated_days: 0.5
id: ticket-278
pr_number: 161
priority: high
status: done
title: The pipeline's own log lines no longer make the clean-tree check refuse the
  next ticket
type: fix
---

# ticket-278 — Le journal du pipeline ne fait plus refuser le ticket suivant

## Objectif

Qu'une file ne s'arrête plus sur « l'arbre contient des modifications que le
pipeline n'a pas faites » quand ces modifications sont celles du pipeline.

## Contexte

Constaté le 2026-10-01 sur `carriere` (`artifacts: tracked`). L'utilisateur
lance une file contenant des tickets déjà terminés (006, 007, 010) puis 012.
`Orchestrator.run_queue` (`services/orchestrator.py`) saute les premiers en
écrivant, via `_log`, « ticket-006 sauté : déjà terminé » dans
`memory/pipeline-log.md` — **fichier suivi** par git dans ce projet. Puis
`ensure_clean_tree` (`services/pipeline_stages.py`) voit ce fichier modifié et
refuse le 012 : `dirty_working_tree`, ticket passé en `blocked`, file
interrompue.

Le pipeline s'est donc refusé lui-même. Le message « modifications que le
pipeline n'a pas faites » était faux.

## Solution proposée

- `ensure_clean_tree` (ou `GitWorkspaceService.is_clean`) ignore les chemins
  que le pipeline écrit lui-même et commite par son suivi : le journal
  `memory/pipeline-log.md` et les fichiers de `tickets/`. Une modification
  ailleurs reste un refus.
- La liste de ces chemins vit à un seul endroit, partagée avec ce que le diff
  relu exclut déjà (`current_diff` exclut tickets et journal).

## Critères d'acceptation

- [ ] Un test montre qu'un arbre dont seul `memory/pipeline-log.md` est modifié
      est considéré propre par le contrôle de démarrage.
- [ ] Un test montre qu'un arbre dont seul un fichier de `tickets/` est modifié
      est considéré propre.
- [ ] Un test montre qu'une modification d'un autre fichier suivi est toujours
      refusée.
- [ ] Un test montre qu'une file dont les premiers tickets sont déjà terminés
      lance le premier ticket restant sans refus.

## Dépendances

Aucune.

## Estimation

Une demi-journée. Backend uniquement.

## Risques

Le journal modifié doit rester commité par le suivi du run suivant, pas
perdu : vérifier qu'il entre dans un commit de suivi.