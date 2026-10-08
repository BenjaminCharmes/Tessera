---
id: ticket-386
title: "In a queue, the between-rounds spending check looks at the current ticket's own spending, not the whole queue's"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: ["ticket-383"]
estimated_days: 0.5
created: 2026-10-08
---

# ticket-386 — En file, le contrôle entre deux tours regarde la dépense du ticket

## Objectif

Qu'un ticket d'une file ne soit plus coupé au milieu de ses tours parce que
les tickets **précédents** ont dépensé.

## Contexte

Entre deux tours, `Orchestrator.run_pipeline`
(`backend/src/tessera/services/orchestrator.py`, `round_num > 1 and
self.budget_exhausted()`) compare `self._spent_usd` à `run_max_budget_usd`,
puis bloque le ticket (`finish_budget_exhausted`,
`backend/src/tessera/services/pipeline_outcomes.py`, ticket-191). En lancement
simple, c'est un plafond par ticket. Mais en file, `_spent_usd` cumule la
dépense de **tous** les tickets déjà passés.

Constaté le 2026-10-08 à 09:02:12 UTC sur vigie (file 007 à 015), signalé par
la session qui pilote ce projet : « [ticket-011] BLOCKED après le tour 1 — run
budget exhausted: 15.24 USD spent of 15.00 allowed ». Le contrôle entre deux
tickets ne s'était pas déclenché (sous 15 $ à la fin du 010) ; le ticket-011,
qui n'avait que deux erreurs mypy à corriger, a perdu son tour 2 et est passé
en `blocked`.

## Solution proposée

1. Le contrôle entre deux tours compare la dépense **du ticket en cours**
   (depuis son premier tour) au plafond par ticket `run_max_budget_usd`. Le
   cumul de la file reste contrôlé entre deux tickets (ticket-383).
2. Si ce contrôle coupe un ticket d'une file, le ticket repasse en `todo`
   (et non `blocked`), avec la raison « budget » dans le journal ; son
   travail reste commité comme non approuvé.
3. Tout arrêt sur un plafond dit le montant atteint et le plafond, par
   exemple « file interrompue : plafond de dépense (15,24 $ / 15,00 $) » —
   aujourd'hui, la ligne d'arrêt de la file n'en dit rien et il faut lire
   `/limits` (signalé par la session qui pilote affut).

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_orchestrator.py` fait tourner une file où le premier ticket coûte 12 $, puis vérifie que le second ticket, qui coûte 4 $ par tour avec `run_max_budget_usd` à 15 $, n'est pas arrêté entre ses tours 1 et 2
- [ ] Un test de `backend/tests/test_orchestrator.py` vérifie qu'un ticket dont sa propre dépense dépasse `run_max_budget_usd` est arrêté entre deux tours
- [ ] Un test de `backend/tests/test_orchestrator.py` vérifie qu'un ticket de file arrêté sur le plafond repasse en `todo`, avec une ligne de journal qui contient « budget »
- [ ] Un test de `backend/tests/test_orchestrator.py` vérifie que la ligne « file interrompue : plafond de dépense » du journal contient le montant dépensé et le plafond
- [ ] Un test de `backend/tests/test_orchestrator.py` vérifie qu'en lancement simple, le comportement du ticket-191 est inchangé

## Dépendances

ticket-383 (plafond de la file proportionnel au nombre de tickets).

## Estimation

0,5 jour.

## Risques

Aucun pour le lancement simple, où dépense du run et dépense du ticket se
confondent.

## Ce que ça ne fait pas

- Ne change pas le plafond par appel d'agent (`LLM_MAX_BUDGET_USD`).
