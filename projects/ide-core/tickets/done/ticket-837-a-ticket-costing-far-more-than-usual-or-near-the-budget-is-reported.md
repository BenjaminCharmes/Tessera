---
id: ticket-837
title: "A ticket costing far more than usual, or near the budget, is reported"
type: feat
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: [ticket-836]
estimated_days: 1
created: 2026-11-05
---

# ticket-837 — Un ticket bien plus cher que d'habitude, ou près du budget, est signalé

## Objectif

La règle `cout_anormal` (ADR-078) : le coût du ticket dépasse `max(3 × médiane, 0,50 USD)`, ou un
run autonome atteint 80 % de `run_max_budget_usd`.

## Contexte

Spec `docs/superpowers/specs/2026-11-05-detecteur-d-anomalies-design.md`. ADR-020 vérifie ses
plafonds **entre** deux tickets et interdit d'en interrompre un : le détecteur le **dit** en cours
de ticket, il n'agit pas. Les enveloppes `queue` et `autonomous` ne portent aucun appel d'agent ;
le coût d'un ticket est celui de sa ligne `single`.

## Solution

- `regles_historiques.py` : `cout_anormal(cout_usd, passes_usd, *, plancher_usd=0.5,
  cumul_usd=None, budget_usd=None)`. Deux clés : `cout_median:<id de la ligne du ticket>` et
  `cout_budget:<run_id>`. Le budget ne vaut que si `budget_usd` est fourni (run `autonomous`).
- `lecture_historique.py` gagne `couts_passes(db_path, project_id, n=20)` (somme d'`agent_calls`
  par run `single` fini du projet, coût > 0, plus récents d'abord),
  `ligne_ouverte_du_ticket(db_path, project_id, ticket_id) -> LigneOuverte | None` (la ligne
  `single` sans `finished_at`) et `cout_du_ticket(db_path, run_row_id) -> float`.

## Critères d'acceptation

- [x] `test_cout_anormal_just_under_three_medians_is_none` et
      `test_cout_anormal_just_over_three_medians_reports` (médiane 2,00 USD : 5,99 puis 6,01)
- [x] `test_cout_anormal_floor_under_is_none` et `test_cout_anormal_floor_over_reports`
      (médiane 0,10 USD : 0,49 puis 0,51)
- [x] `test_cout_anormal_without_enough_samples_skips_the_median_rule` (9 échantillons)
- [x] `test_cout_anormal_budget_at_79_percent_is_none` et
      `test_cout_anormal_budget_at_80_percent_reports` (3,99 puis 4,00 USD sur 5,00)
- [x] `test_cout_anormal_without_a_budget_never_reports_the_budget_rule`
- [x] `test_couts_passes_keeps_the_20_most_recent_single_runs_of_the_project` (enveloppes,
      autre projet, runs non finis et coût nul exclus)
- [x] `test_ligne_ouverte_du_ticket_returns_the_unfinished_single_row_only`
- [x] `test_cout_du_ticket_sums_the_calls_of_its_row`

## Ce que ça ne fait pas

N'arrête jamais un run sur le coût : ADR-020 reste la seule porte. Ne touche ni `cost_aggregate`
ni les plafonds existants.
