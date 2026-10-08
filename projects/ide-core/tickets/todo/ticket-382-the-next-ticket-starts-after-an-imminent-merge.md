---
id: ticket-382
title: "On a project that merges without CI, the next ticket of a queue starts from the base that holds the previous ticket"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-08
---

# ticket-382 — Le ticket suivant part de la base qui contient le précédent

## Objectif

Que deux tickets successifs d'une file ne se retrouvent plus en conflit pour
la seule raison que le second est parti avant le merge du premier.

## Contexte

Dans `run_queue` (`backend/src/tessera/services/orchestrator.py`), quand la
PR d'un ticket est ouverte, la phase 2 (attente de la CI, merge) est confiée
au `CIWatcher` et le ticket suivant démarre aussitôt (ADR-051). La seule
attente est celle d'un ticket qui déclare le précédent dans son `depends_on`
(`_attendre_si_dependant`).

Sur un projet en `merge_without_ci: true`, le merge suit la PR de quelques
secondes. Mais le ticket suivant a déjà créé sa branche sur l'ancienne base.
Comme la documentation réécrit les mêmes fichiers à chaque ticket
(`memory/architecture.md`, guides), le rebase de livraison du second ticket
entre en conflit.

Constaté le 2026-10-08 sur affut : le ticket-011 est parti de `main` au
ticket-009, juste après l'ouverture de la PR du ticket-018 et avant son
merge ; livraison arrêtée sur « Conflit avec main sur :
backend/tests/test_database.py, memory/architecture.md », file interrompue.

## Solution proposée

Quand le projet déclare `merge_without_ci: true` et que la PR du ticket qui
vient d'être livré est confiée au `CIWatcher`, la file **attend son merge**
(`ci_watcher.attendre_merge`) avant de passer au ticket suivant, que celui-ci
en dépende ou non, avec un plafond (réglage `attente_merge_max_s`, 600 s par
défaut). Ensuite, la base du ticket suivant est réalignée sur la base
distante (`sync_base_depuis_distant`) avant la création de sa branche.

Un projet dont le merge attend une vraie CI garde le comportement actuel :
attendre des minutes de CI annulerait le gain d'ADR-051.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_orchestrator_livraison.py` fait tourner une file de deux tickets indépendants sur un projet `merge_without_ci: true` et vérifie que le second ticket ne démarre qu'après le signal de merge du premier
- [ ] Un test de `backend/tests/test_orchestrator_livraison.py` vérifie que, sur un projet sans `merge_without_ci`, le second ticket indépendant démarre sans attendre le merge du premier
- [ ] Un test de `backend/tests/test_orchestrator_livraison.py` vérifie que la base est réalignée sur la base distante avant la création de la branche du second ticket
- [ ] Un test de `backend/tests/test_orchestrator_livraison.py` vérifie qu'au-delà de `attente_merge_max_s` la file passe au ticket suivant, avec une ligne de journal qui le dit

## Dépendances

Aucune.

## Estimation

0,5 jour.

## Risques

Le verrou du projet est tenu quelques secondes de plus par ticket : c'est le
prix d'une base à jour.

## Ce que ça ne fait pas

- Ne résout pas les conflits ; `resolveur-conflit` (ADR-033) reste le recours.
- Ne change rien aux projets dont le merge attend la CI.
