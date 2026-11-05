---
id: ticket-808
title: "A route reads and writes the settings from a declared origin only"
type: feat
status: todo
pr_number: null
priority: low
agent: codeur
depends_on: ["ticket-805"]
estimated_days: 1
created: 2026-11-05
---

# ticket-808 — Une route lit et écrit les réglages, depuis une origine déclarée seulement

## Objectif

`GET`, `PUT` et `DELETE` sur `/api/v1/reglages`, avec un contrôle d'`Origin` plus strict que celui
du reste de l'API sur les écritures.

## Contexte

ADR-075, design §4 et §5. L'API est ouverte quand `STATIC_TOKEN` est vide. Le contrôle d'`Origin`
actuel admet tout port loopback en HTTP et un `Origin` absent (ticket-754 ne ferme que les
WebSocket) : insuffisant pour relever un plafond de dépense.

## Ce que le ticket fait

- `backend/src/tessera/routers/reglages.py` : les trois routes du design §5, branchées dans `main.py`.
  `GET` rend `runs_ouverts` depuis `RunRegistry`.
- `backend/src/tessera/auth.py` : sur `PUT` et `DELETE` d'un chemin `/api/v1/reglages…`, `Origin`
  obligatoire et présent dans `_declared_origins()` ; absent ou hors liste, 403. Les autres routes et
  `GET` ne changent pas.
- Un nom hors registre rend 404, secrets compris, sans le nommer dans le message.
- Chaque écriture journalise `reglage_modifie` avec `nom`, `ancienne` et `nouvelle`.

## Tests (`backend/tests/test_routes_reglages.py`)

- `test_get_lists_the_five_settings_with_default_bounds_and_effect`
- `test_put_with_a_declared_origin_changes_the_value`
- `test_put_without_origin_is_forbidden`
- `test_put_from_a_loopback_port_that_is_not_declared_is_forbidden`
- `test_put_from_the_tauri_origin_is_accepted`
- `test_put_from_an_origin_added_by_allowed_origins_is_accepted`
- `test_delete_returns_the_setting_to_its_default`
- `test_put_out_of_bounds_is_422_and_zero_for_a_budget_is_422`
- `test_put_a_secret_name_is_404_and_the_message_does_not_name_it`
- `test_get_without_origin_still_works`
- `test_static_token_is_still_required_when_set`
- `test_runs_ouverts_counts_the_open_runs`
- `test_put_logs_the_name_and_both_values`
- `test_other_routes_keep_accepting_a_request_without_origin` : le contrôle ne déborde pas

## Critères d'acceptation

- [ ] Les tests ci-dessus passent, `backend/tests/test_auth*.py` existants inchangés et verts
- [ ] `routers/reglages.py` reste sous 150 lignes ; `auth.py` sous 300

## Ce que ça ne fait pas

Le garde de `Bash` (ticket-809) et l'interface (810).
