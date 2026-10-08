---
agent: codeur
created: 2026-10-07
depends_on: []
estimated_days: 0.5
id: ticket-378
pr_number: null
priority: high
status: done
title: After delivery, the delivery log lines are committed and the working tree is
  back, clean, on the base branch
type: fix
---

# ticket-378 — Après livraison, l'arbre est propre et revenu sur la branche de base

## Objectif

Qu'un run livré ne laisse plus `memory/pipeline-log.md` modifié hors commit,
ni la copie de travail sur la branche du ticket.

## Contexte

Les lignes de livraison (« livraison: rebase sur … », « PR #NN ouverte »,
« confiée au CIWatcher ») sont écrites dans `memory/pipeline-log.md` par
`backend/src/tessera/services/orchestrator.py` **après** le dernier commit du
run (le commit de suivi poussé après l'ouverture de la PR,
`post_pr_callback`, `backend/src/tessera/services/livraison.py`).

Conséquences, constatées le 2026-10-07 sur carriere, ide-core et affut :

- l'arbre n'est plus propre après un run (ADR-018) ;
- la copie de travail reste sur `ticket-0XX` au lieu de revenir sur la
  branche de base, et `git checkout <base>` échoue tant que le journal n'est
  pas mis de côté ;
- il faut un `git stash` à la main à chaque fois : carriere en avait
  accumulé six (`ticket-018` à `ticket-063`), ide-core plus de vingt.

## Solution proposée

1. Écrire les lignes de livraison de la phase 1 **avant** le commit de suivi
   poussé après l'ouverture de la PR, pour qu'elles en fassent partie ; une
   ligne écrite plus tard (merge par le `CIWatcher`) est commitée et poussée
   avec le suivi de la phase 2.
2. En fin de run livré, revenir sur la branche de base du projet, arbre
   propre. Aucun commit n'est créé sur la branche de base.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_orchestrator_livraison.py` livre un run dans un dépôt temporaire avec un dépôt distant simulé, et vérifie qu'ensuite `git status --porcelain --untracked-files=no` est vide
- [ ] Un test de `backend/tests/test_orchestrator_livraison.py` vérifie qu'après la livraison, la ligne « PR #… ouverte » figure dans `memory/pipeline-log.md` du dernier commit de la branche du ticket
- [ ] Un test de `backend/tests/test_orchestrator_livraison.py` vérifie qu'après la livraison, la copie de travail est sur la branche de base
- [ ] Un test de `backend/tests/test_orchestrator_livraison.py` vérifie que la branche de base locale n'a reçu aucun commit pendant la livraison

## Dépendances

Aucune.

## Estimation

0,5 jour.

## Risques

Le commit de suivi poussé après la PR existe déjà (il porte le `pr_number`) :
y ajouter les lignes de livraison ne déclenche pas de run de CI
supplémentaire.

## Ce que ça ne fait pas

- Ne sort pas `pipeline-log.md` du dépôt.
- Ne supprime pas le doublon de CI dû au commit poussé après l'ouverture de
  la PR.