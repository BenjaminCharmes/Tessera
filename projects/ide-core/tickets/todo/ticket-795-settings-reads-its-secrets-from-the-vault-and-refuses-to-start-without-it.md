---
id: ticket-795
title: "Settings reads its secrets from the vault and refuses to start without it"
type: feat
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: ["ticket-794"]
estimated_days: 1
created: 2026-11-05
---

# ticket-795 — `Settings` lit ses secrets dans le coffre et refuse de démarrer sans lui

## Objectif

Les neuf secrets de `Settings` viennent du coffre, avec l'ordre et les refus fixés par
ADR-073.

## Contexte

`docs/superpowers/specs/2026-11-05-secrets-dans-le-coffre-design.md`, §3. Aujourd'hui
`backend/src/tessera/config.py` lit `.env` et l'environnement seuls.

## Ce que le ticket fait

- `secrets_source: Literal["coffre", "env"] = "coffre"` dans `Settings`, lu avant le reste
  (variable d'environnement, puis `.env` par `dotenv_values`).
- `SourceCoffre(PydanticBaseSettingsSource)` et `settings_customise_sources` : init, variables
  d'environnement, coffre, `.env`, défauts. En mode `env`, la source n'existe pas et
  `coffre_du_systeme()` n'est jamais appelé.
- Mode `coffre` : `CoffreAbsent` ou `CoffreEnErreur` deviennent une `ConfigurationError` sans
  valeur, qui nomme `SECRETS_SOURCE=env` pour le premier. Une entrée absente se replie sur
  `.env` puis sur le défaut vide ; chaque secret lu dans `.env` journalise
  `secret_en_clair_dans_env` (le nom seul).
- `backend/tests/conftest.py` pose `SECRETS_SOURCE=env` avant tout import de `tessera.config`,
  pour que la suite ne touche jamais le coffre de la machine ni la CI un coffre absent.

## Tests (`backend/tests/test_config_coffre.py`)

- `test_coffre_value_wins_over_dotenv`
- `test_environment_variable_wins_over_the_vault`
- `test_missing_entry_falls_back_to_dotenv_and_warns_by_name_only`
- `test_missing_entry_everywhere_keeps_the_empty_default`
- `test_absent_vault_in_coffre_mode_refuses_to_start` : message sans valeur, qui cite `env`.
- `test_locked_vault_in_coffre_mode_refuses_to_start`
- `test_env_mode_never_calls_the_vault` : un `Coffre` qui lève à l'appel.
- `test_secrets_source_is_read_from_dotenv_when_not_in_the_environment`
- `test_validation_error_for_a_vault_value_does_not_echo_it`

## Critères d'acceptation

- [ ] L'ordre de lecture et les cinq lignes du tableau du §3 sont couverts par un test chacun
- [ ] `backend/tests/conftest.py` est nommé et modifié : la suite complète passe sans coffre
- [ ] Un démarrage manuel de `make dev` sans coffre ni `SECRETS_SOURCE=env` échoue avec un
      message lisible, pas une trace

## Ce que ça ne fait pas

Ni masquage des nouveaux secrets (ticket-796), ni migration (ticket-797).

## Risques

Ce ticket modifie `backend/tests/conftest.py`, signalé par la porte de configuration des
tests : le chemin complet est nommé ici, c'est voulu.
