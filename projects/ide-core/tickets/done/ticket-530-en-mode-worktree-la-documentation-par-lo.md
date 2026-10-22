---
agent: codeur
created: '2026-10-22'
depends_on: []
id: ticket-530
pr_number: 596
priority: medium
status: done
title: En mode worktree, la documentation par lot écrit dans le checkout du projet
type: fix
---

## Signalement

- Projet source : kadoomi
- Nature : bug
- Reçu le : 2026-10-22

## Description

Run d6737be6 (kadoomi, ticket-090 seul, worktree ADR-056), 22/10 08:33-08:41 UTC. Le run a codé, testé et livré dans ~/.tessera/worktrees/kadoomi/ticket-090, mais l étape documentation (doc_updated) a écrit dans projects/kadoomi : docs/architecture.md, docs/guide-utilisateur.md et memory/documentation.json sont modifiés dans le checkout (develop), hors de toute branche et hors de la PR #115. Or ADR-056 dit que le checkout n est jamais écrit par un run. Le lot couvre en plus les tickets 077-086, faits à la main, et non le ticket du run.

## Contexte

Événement doc_updated du run d6737be6405343ddab570fe12f316b6f, fichiers sous C:UsersBenjamin.CHARMESDesktop	esseraprojectskadoomidocs. Contournement : aucun, les fichiers sont laissés tels quels dans le checkout en attendant la décision d ide-core.

## Cause (triage ide-core, 22/10)

`_documenteur` de `routers/orchestrator.py` calcule `project_path` sur le
dossier réel et `racine_ecriture(project_path)` sans worktree ; il ne reçoit
jamais `wt`. Tout le reste du run reçoit `wt.projet` (`racine_run`). Le commit
`docs: update documentation for …` part donc dans le worktree, alors que les
fichiers ont été écrits dans le checkout.

## Solution proposée

Passer le worktree du run à `_documenteur` : avec un worktree, il lit les
tickets, écrit `memory/documentation.json` et cherche `README.md`/`docs/` dans
le dossier du projet **dans le worktree**, et `racine_doc` vient de
`racine_ecriture(project_path, wt)`. Sans worktree, rien ne change.

## Critères d'acceptation

- [ ] `_documenteur` de `routers/orchestrator.py` reçoit le worktree du run, et l'appel qui le construit le lui passe
- [ ] Avec un worktree, `mettre_a_jour` reçoit le dossier du projet dans le worktree, et `racine_doc` est `racine_ecriture(project_path, wt)`
- [ ] Un test vérifie, avec des doubles de fournisseur LLM, qu'une documentation faite pour un run à worktree écrit sous le worktree et laisse le dossier réel du projet sans aucun fichier modifié
- [ ] Un test vérifie que, sans worktree, `_documenteur` écrit toujours sous `racine_ecriture(project_path)` du dossier réel

## Ce que ça ne fait pas

- Ne change pas la sélection du lot : les tickets faits à la main restent
  documentés avec le run suivant (ADR-035).