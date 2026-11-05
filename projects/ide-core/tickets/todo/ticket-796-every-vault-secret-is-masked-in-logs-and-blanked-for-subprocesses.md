---
id: ticket-796
title: "Every vault secret is masked in logs and blanked for subprocesses"
type: fix
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: ["ticket-795"]
estimated_days: 1
created: 2026-11-05
---

# ticket-796 — Chaque secret du coffre est masqué dans les logs et vidé pour les sous-processus

## Objectif

Les huit secrets qui ne sont pas `FORBIDDEN_TERMS` sont masqués dans les logs, refusés par la
porte de push et absents de l'environnement du CLI.

## Contexte

`Settings.valeurs_des_jetons()` ne couvre que les cinq jetons de mise en ligne : `GITHUB_TOKEN`,
`STATIC_TOKEN` et `ANTHROPIC_API_KEY` ne sont ni masqués ni traités comme termes interdits
aujourd'hui. Design §4.

## Ce que le ticket fait

- `Settings.valeurs_des_secrets()` rend les valeurs non vides des huit secrets ; ni
  `FORBIDDEN_TERMS`, ni les identifiants non secrets. `valeurs_des_jetons` est retiré et ses
  appelants (`utils/secrets.py`, `services/termes_interdits.py`, le logger) passent au nouveau nom.
- `env_du_sous_processus` vide aussi `STATIC_TOKEN` et `FORBIDDEN_TERMS`. `GITHUB_TOKEN` n'est
  pas touché : voir « Ce que ça ne fait pas ».

## Tests

- `backend/tests/test_secrets_registry.py` : `test_all_eight_secrets_are_registered_at_startup`,
  `test_forbidden_terms_is_not_registered_as_a_secret`.
- `backend/tests/test_env_sdk.py` (existant ou nouveau) :
  `test_subprocess_env_blanks_static_token_and_forbidden_terms`,
  `test_subprocess_env_keeps_the_git_bash_path`.
- `backend/tests/test_termes_interdits.py` (existant ou nouveau) :
  `test_a_github_token_in_a_diff_line_is_a_violation`.
- `test_a_github_token_is_masked_in_a_log_line` dans les tests du logger.

## Critères d'acceptation

- [ ] Aucun appelant de `valeurs_des_jetons` ne subsiste (`Grep` dans `backend/`)
- [ ] Les quatre familles de tests passent
- [ ] La liste des variables vidées vient de `NOMS_SECRETS`, pas d'une seconde liste

## Ce que ça ne fait pas

Vider `GITHUB_TOKEN` et `GH_TOKEN` pour les agents : leurs lectures `gh` (ADR-067) peuvent en
dépendre, à mesurer avant (design §9). Le typage en `SecretStr` des trois champs `str`.
