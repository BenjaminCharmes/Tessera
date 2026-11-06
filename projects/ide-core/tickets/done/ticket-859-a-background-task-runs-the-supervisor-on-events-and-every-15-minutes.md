---
agent: codeur
created: 2026-11-05
depends_on:
- ticket-855
- ticket-856
- ticket-857
- ticket-858
estimated_days: 1
id: ticket-859
pr_number: 957
priority: high
status: done
title: A background task runs the supervisor on events and every 15 minutes
type: feat
---

# ticket-859 — La tâche de fond du superviseur : événements et balayage de 15 minutes

## Objectif

Les quatre actions tournent seules, à la fermeture d'un run ou d'une file et toutes les
15 minutes, sans jamais se doubler ni dépasser le plafond du jour.

## Contexte

ADR-080, spec §2 « Quand il tourne ». Le détecteur d'anomalies (ADR-078, ticket-839) a déjà sa
tâche de fond (5 min) : copier sa forme, ne pas la modifier. Il reste sans LLM, sans `git`.

## Ce qu'il faut faire

- `services/supervision/superviseur_boucle.py` : démarre avec le backend si le rôle
  `superviseur` est déclaré actif dans un projet (désactivé par défaut) ; s'accroche à
  `RUN_REGISTRY.sur_fermeture` et balaie toutes les 15 min, décalé du détecteur.
- Clé d'idempotence `action:cible:sha` tenue en mémoire et dans `ide_state_dir` ; deux échecs
  de suite sur une clé : verdict `a_toi`, plus de tentative.
- Dépense du jour (appels du superviseur dans la base d'usage) comparée à `budget_jour_usd` ;
  atteint : les actions sans modèle continuent, les autres attendent le lendemain.
- Événement `superviseur_action` (cloche, historique) par action ; la tâche n'interrompt jamais
  un run et son échec n'atteint aucun run (ADR-037).

## Critères d'acceptation

- [ ] `test_superviseur_boucle.py::test_run_closing_triggers_one_pass`
- [ ] `test_superviseur_boucle.py::test_second_pass_repeats_nothing`
- [ ] `test_superviseur_boucle.py::test_two_failures_on_a_key_go_to_a_toi`
- [ ] `test_superviseur_boucle.py::test_spent_daily_budget_keeps_only_model_free_actions`
- [ ] `test_superviseur_boucle.py::test_inactive_role_starts_nothing`
- [ ] `test_superviseur_boucle.py::test_an_exception_never_reaches_a_run`

## Ce que ça ne fait pas

Ne modifie pas le détecteur. N'écrit pas `agents.json` : activer le rôle est le geste de Benjamin.