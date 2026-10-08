---
id: ticket-383
title: "A queue's spending ceiling scales with its number of tickets, and stopping on it is visible"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-08
---

# ticket-383 — Le plafond de dépense d'une file suit son nombre de tickets

## Objectif

Qu'une file choisie ticket par ticket ne s'arrête plus au milieu sur un
plafond pensé pour le mode autonome, et qu'un arrêt pour budget se voie.

## Contexte

`Orchestrator.budget_exhausted` (`backend/src/tessera/services/orchestrator.py`)
compare la dépense cumulée du run à `run_max_budget_usd` (5 $ par défaut,
`backend/src/tessera/config.py`, ADR-020). Ce plafond a été pensé pour le
mode autonome (« jusqu'à 5 tickets ») ; `run_queue` l'applique tel quel à une
file, quelle que soit sa longueur.

Constaté le 2026-10-08 sur vigie : file de 15 tickets (run c776276d), arrêtée
après 6 sur « [vigie] file interrompue : plafond de dépense » (07:59:01 UTC),
sans autre signal que cette ligne de journal. Signalé par la session qui
pilote vigie.

## Solution proposée

1. En mode `queue`, le plafond vaut `run_max_budget_usd` × nombre de tickets
   de la file, sauf si la requête en fixe un autre.
2. `RunRequest` (`backend/src/tessera/routers/orchestrator.py`) accepte un
   champ optionnel `budget_usd` qui, s'il est donné, remplace ce calcul (pour
   la file comme pour le mode autonome).
3. Un arrêt sur le plafond émet un événement `queue_progress` (ou équivalent
   déjà affiché par l'interface) portant la raison `budget`, en plus de la
   ligne de journal.

Le mode autonome garde son plafond actuel.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_orchestrator.py` fait tourner une file de 3 tickets dont chacun coûte 4 $ avec `run_max_budget_usd` à 5 $, et vérifie que les 3 tickets s'exécutent
- [ ] Un test de `backend/tests/test_orchestrator.py` vérifie que la même file s'arrête avant le 3e ticket quand la requête fixe `budget_usd` à 6 $
- [ ] Un test de `backend/tests/test_orchestrator.py` vérifie qu'un arrêt sur le plafond émet un événement dont les données portent la raison `budget`
- [ ] Un test de `backend/tests/test_orchestrator.py` vérifie que le mode autonome garde `run_max_budget_usd` comme plafond

## Dépendances

Aucune.

## Estimation

0,5 jour.

## Risques

Une longue file peut dépenser davantage avant de s'arrêter : c'est le
nombre de tickets que l'utilisateur a lui-même choisi. Le contrôle du quota
réel (ADR-020) reste en place entre deux tickets.

## Ce que ça ne fait pas

- Ne change pas le plafond par run du pipeline (dépense d'un seul ticket).
- N'ajoute pas de réglage dans l'interface.
