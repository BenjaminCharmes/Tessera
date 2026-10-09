---
agent: codeur
created: 2026-10-09
depends_on: []
estimated_days: 0.5
id: ticket-390
pr_number: null
priority: high
status: done
title: A run that ends without a PR commits its bookkeeping and returns the tree to
  its base branch
type: fix
---

# ticket-390 — Un run qui finit sans PR remet l'arbre sur sa base

## Objectif

Qu'à la fin de tout run, livré ou non, l'arbre du projet soit propre et sur
sa branche de base.

## Contexte

Le ticket-378 (`Orchestrator._finaliser_livraison`,
`backend/src/tessera/services/orchestrator.py`) commite les lignes de journal
puis revient sur la base, mais seulement quand la livraison a ouvert une PR
(`livraison.pr_number` non nul). Constaté le 2026-10-09 :

- 12:37 UTC, ticket-383 bloqué par l'audit sécurité : commit « unapproved »,
  puis la ligne « file interrompue » écrite **après** le commit de
  bookkeeping. L'arbre de Tessera est resté sur `ticket-383-…`, avec
  `memory/pipeline-log.md` modifié.
- 12:28 UTC, ticket-382, livraison arrêtée sur un conflit : aucune PR, donc
  pas de retour sur la base non plus.

Pour ide-core, c'est dangereux : le backend charge son code depuis cet arbre.
Un import paresseux ou un redémarrage lirait alors le code d'un ticket refusé
(cf. le mélange de versions du 2026-10-08).

## Solution proposée

1. En fin de `run_pipeline` (run seul) et en fin de `run_queue` (après la
   dernière ligne de journal, y compris « file interrompue »), si un
   espace git et une branche de base sont connus : `commit_bookkeeping()`,
   puis `retourner_sur_base(base_branch)`.
2. Les erreurs sont journalisées sans être levées, comme dans
   `_finaliser_livraison`.
3. Le retour sur la base ne touche pas à la branche du ticket : son commit
   « unapproved » reste où il est.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_orchestrator_livraison.py` fait tourner une file dont le ticket est refusé par l'audit sécurité et vérifie que `retourner_sur_base` est appelé avec la branche de base après l'écriture de la ligne « file interrompue »
- [ ] Un test de `backend/tests/test_orchestrator_livraison.py` vérifie qu'une livraison arrêtée sur un conflit (sans `pr_number`) appelle `commit_bookkeeping` puis `retourner_sur_base`
- [ ] Un test de `backend/tests/test_orchestrator_livraison.py` vérifie qu'une exception levée par `retourner_sur_base` ne fait pas échouer le run
- [ ] Un test de `backend/tests/test_orchestrator_livraison.py` vérifie que la ligne « file interrompue » est incluse dans un commit de bookkeeping, et qu'aucune modification de `memory/pipeline-log.md` ne reste hors commit

## Dépendances

Aucune.

## Estimation

0,5 jour.

## Risques

Un run seul lancé à la main pour inspecter son résultat ne laisse plus l'arbre
sur la branche du ticket : il faut faire un `git checkout` pour la relire.
C'est voulu (ADR-018 : l'arbre ne reste jamais sale ni ailleurs).

## Ce que ça ne fait pas

- Ne change pas la reprise au démarrage (tickets 369, 375, 389).