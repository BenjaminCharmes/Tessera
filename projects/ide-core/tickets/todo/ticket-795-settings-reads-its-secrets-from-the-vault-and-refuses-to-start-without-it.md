---
id: ticket-795
title: "Settings reads its secrets from the vault when it holds them, and from .env otherwise"
type: feat
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: ["ticket-794"]
estimated_days: 1
created: 2026-11-05
---

# ticket-795 — `Settings` lit ses secrets dans le coffre quand il les porte, sinon dans `.env`

## Objectif

Les neuf secrets de `Settings` viennent du coffre quand il les porte, avec l'ordre fixé par
ADR-073 ; une machine sans coffre continue de démarrer sur son `.env`.

## Contexte

`docs/superpowers/specs/2026-11-05-secrets-dans-le-coffre-design.md`, §3. Aujourd'hui
`backend/src/tessera/config.py` lit `.env` et l'environnement seuls.

**Décision de Benjamin, 05/11 :** Tessera doit rester utilisable facilement depuis tous ses PC.
Le mode par défaut est donc `auto` (coffre s'il répond, sinon `.env`, avec un avertissement),
et non `coffre` (refus de démarrer sans coffre) comme dans le design d'origine. Le mode strict
`coffre` reste disponible, sur déclaration.

## Ce que le ticket fait

- `secrets_source: Literal["auto", "coffre", "env"] = "auto"` dans `Settings`, lu avant le
  reste (variable d'environnement, puis `.env` par `dotenv_values`).
- `SourceCoffre(PydanticBaseSettingsSource)` et `settings_customise_sources` : init, variables
  d'environnement, coffre, `.env`, défauts. En mode `env`, la source n'existe pas et
  `coffre_du_systeme()` n'est jamais appelé.
- Mode `auto` : `CoffreAbsent` ou `CoffreEnErreur` désactivent la source coffre ; les secrets
  viennent de `.env`, et le démarrage journalise une fois `coffre_indisponible_repli_env` (sans
  valeur). **Exception** : si `.env` porte une ligne `# NOM : dans le coffre` (secret migré par
  ticket-797), le coffre indisponible devient une `ConfigurationError` comme en mode `coffre` —
  un `STATIC_TOKEN` ou un `FORBIDDEN_TERMS` migré ne doit jamais tomber vide en silence
  (design §3).
- Mode `coffre` : `CoffreAbsent` ou `CoffreEnErreur` deviennent une `ConfigurationError` sans
  valeur, qui nomme `SECRETS_SOURCE=auto` et `env`.
- Dans tous les modes, une entrée absente du coffre se replie sur `.env` puis sur le défaut
  vide ; chaque secret lu dans `.env` journalise `secret_en_clair_dans_env` (le nom seul).
- `backend/tests/conftest.py` pose `SECRETS_SOURCE=env` avant tout import de `tessera.config`,
  pour que la suite ne touche jamais le coffre de la machine ni la CI un coffre absent.

## Tests (`backend/tests/test_config_coffre.py`)

- `test_coffre_value_wins_over_dotenv`
- `test_environment_variable_wins_over_the_vault`
- `test_missing_entry_falls_back_to_dotenv_and_warns_by_name_only`
- `test_missing_entry_everywhere_keeps_the_empty_default`
- `test_absent_vault_in_auto_mode_starts_on_dotenv_and_warns_once`
- `test_locked_vault_in_auto_mode_starts_on_dotenv`
- `test_absent_vault_in_auto_mode_refuses_when_dotenv_marks_a_migrated_secret`
- `test_absent_vault_in_coffre_mode_refuses_to_start` : message sans valeur, qui cite `auto`.
- `test_env_mode_never_calls_the_vault` : un `Coffre` qui lève à l'appel.
- `test_secrets_source_defaults_to_auto`
- `test_validation_error_for_a_vault_value_does_not_echo_it`

## Critères d'acceptation

- [ ] Les tests ci-dessus existent dans `backend/tests/test_config_coffre.py` et passent
- [ ] `test_absent_vault_in_auto_mode_starts_on_dotenv_and_warns_once` vérifie que les secrets
      viennent de `.env` et que l'avertissement ne contient aucune valeur
- [ ] `test_absent_vault_in_auto_mode_refuses_when_dotenv_marks_a_migrated_secret` vérifie le
      refus, message sans valeur
- [ ] `backend/tests/conftest.py` est nommé et modifié : la suite complète passe sans coffre

## Ce que ça ne fait pas

Ni masquage des nouveaux secrets (ticket-796), ni migration (ticket-797).

## Risques

Ce ticket modifie `backend/tests/conftest.py`, signalé par la porte de configuration des
tests : le chemin complet est nommé ici, c'est voulu.
