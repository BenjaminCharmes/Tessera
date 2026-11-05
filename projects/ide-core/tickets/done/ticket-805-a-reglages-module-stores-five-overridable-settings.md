---
agent: codeur
created: 2026-11-05
depends_on: []
estimated_days: 1
id: ticket-805
pr_number: 924
priority: low
status: done
title: A reglages module stores five overridable settings in SQLite
type: feat
---

# ticket-805 — Un module `reglages` range cinq réglages modifiables dans SQLite

## Objectif

Le backend dispose d'une seule porte vers les réglages modifiables : un registre fermé et borné,
une table, un cache. Aucun comportement du backend ne change encore.

## Contexte

ADR-075 et `docs/superpowers/specs/2026-11-05-reglages-globaux-design.md`, §1 à §3 : les
signatures y sont fixées.

## Ce que le ticket fait

- `backend/src/tessera/reglages.py` : `Reglage`, `REGISTRE` (les cinq noms et leurs bornes du
  design), `ReglagesEffectifs`, `ReglageInvalide`, `valider`, `charger`, `ecrire`, `retirer`,
  `du_moment`, `figer`, `courants`.
- Migration 11 de `backend/src/tessera/services/database.py` : table `reglages`.
- `main.py` : `await reglages.charger(settings.ide_db_path)` dans le `lifespan`, après `init_db`.
- `du_moment()` relit `settings.<nom>` à chaque appel ; `figer` pose un `ContextVar`.
- `valider` refuse : un nom hors registre, un type faux (un `bool` pour un `float`, un texte), NaN et
  l'infini, une valeur hors bornes, `0` pour un budget.
- `charger` ignore et journalise une ligne au nom inconnu ou hors bornes.

## Tests (`backend/tests/test_reglages.py`)

- `test_registre_lists_exactly_the_five_names`
- `test_registre_holds_no_secret_no_path_and_no_security_setting` : aucun nom parmi `CHAMPS_JETONS`,
  `static_token`, `forbidden_terms`, `anthropic_api_key`, `github_token`, `allowed_hosts`,
  `allowed_origins`, aucun champ `Path`
- `test_valider_rejects_out_of_bounds_values`, `test_valider_rejects_a_wrong_type`,
  `test_valider_rejects_nan_and_infinity`, `test_valider_refuses_zero_for_a_budget`
- `test_du_moment_returns_the_env_default_without_override`
- `test_du_moment_follows_a_settings_monkeypatch`
- `test_ecrire_then_du_moment_returns_the_override`
- `test_ecrire_survives_a_new_charger_on_the_same_database`
- `test_retirer_returns_to_the_default`
- `test_charger_ignores_an_unknown_name_and_an_out_of_bounds_value`
- `test_ecrire_never_touches_the_env_file`
- `test_figer_keeps_its_values_after_a_later_ecrire`
- `test_courants_outside_a_run_follows_ecrire`
- `test_du_moment_ignores_the_frozen_snapshot`
- `backend/tests/test_database_migrations.py` (ou le test de schéma existant) :
  `test_migration_11_creates_the_reglages_table`

## Critères d'acceptation

- [ ] Les tests ci-dessus passent ; `version_du_schema()` rend 11
- [ ] `reglages.py` ne dépasse pas 200 lignes et n'importe rien de `services/` hors `database`
- [ ] mypy passe

## Ce que ça ne fait pas

Aucun site de lecture n'est migré (tickets 806 et 807), aucune route (808).