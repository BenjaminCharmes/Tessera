---
id: ticket-806
title: "A run keeps the budgets and the dialogue delay it opened with"
type: feat
status: todo
pr_number: null
priority: low
agent: codeur
depends_on: ["ticket-805"]
estimated_days: 1
created: 2026-11-05
---

# ticket-806 — Un run garde les plafonds et le délai de dialogue de son ouverture

## Objectif

Changer `run_max_budget_usd`, `llm_max_budget_usd` ou `dialogue_timeout_s` n'affecte aucun run
ouvert : la nouvelle valeur vaut dès le run suivant.

## Contexte

ADR-075 et le design, §3. Un plafond modifié sous un run qui est en train de le dépasser est
pire qu'un plafond fixe ; et un agent ne doit pas relever le plafond de son propre run.

## Ce que le ticket fait

- `RunActif` (`services/run_registry.py`) porte `reglages: ReglagesEffectifs`, posé par `ouvrir`
  avec `reglages.du_moment()`.
- `routers/orchestrator.py` : après `RUN_REGISTRY.ouvrir`, `reglages.figer(run.reglages)`, avant
  la construction de l'orchestrateur ; la tâche du run en hérite.
- Les lectures passent par `reglages.courants()` : `assemblage_run.py` (`run_max_budget_usd`),
  `routers/orchestrator.py` (`get_limits`), `services/run_executor.py` (`dialogue_du_run`, les deux
  lectures de `dialogue_timeout_s`), `services/providers/par_role.py` (`llm_max_budget_usd`).

## Tests

`backend/tests/test_run_reglages_figes.py` :

- `test_ouvrir_stores_the_values_of_the_moment_in_the_run`
- `test_orchestrator_gets_the_run_budget_frozen_at_opening` : `ecrire` entre `ouvrir` et la
  construction, l'orchestrateur reçoit l'ancienne valeur
- `test_dialogue_channel_uses_the_frozen_timeout`
- `test_provider_budget_follows_the_frozen_value_inside_a_run_and_the_live_one_outside`
- `test_a_task_created_after_figer_inherits_the_snapshot`
- `test_a_second_run_opened_after_ecrire_gets_the_new_values`
- `test_get_limits_returns_the_current_values`

Les tests existants qui posent ces réglages par `monkeypatch` restent verts, sans modification.

## Critères d'acceptation

- [ ] Les tests ci-dessus passent, la suite existante aussi
- [ ] Aucun `settings.run_max_budget_usd`, `settings.llm_max_budget_usd` ni
      `settings.dialogue_timeout_s` ne subsiste hors de `reglages.py` et `config.py`

## Ce que ça ne fait pas

Les deux réglages de machine (ticket-807) et la route (808).
