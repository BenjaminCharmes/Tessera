---
id: ticket-809
title: "The Bash guard refuses network commands that name the settings route"
type: feat
status: todo
pr_number: null
priority: low
agent: codeur
depends_on: ["ticket-799", "ticket-808"]
estimated_days: 1
created: 2026-11-05
---

# ticket-809 — Le garde de `Bash` refuse les commandes réseau qui nomment la route des réglages

## Objectif

Un agent qui lance `curl -X PUT …/api/v1/reglages/run_max_budget_usd` est refusé, avec un message
qui dit le plafond du contrôle.

## Contexte

ADR-075, design §4. L'`Origin` obligatoire (ticket-808) arrête une page et un `curl` nu ; ce garde
arrête l'erreur de l'agent qui essaie. Même module que ticket-799 : il passe après lui, pour ne pas
éditer `garde_jetons.py` en parallèle.

## Ce que le ticket fait

- `backend/src/tessera/services/providers/garde_jetons.py` : un contrôle d'exécution. Refus quand
  le premier mot d'un segment (séparé comme `_COMMANDES`, `.exe` retiré, casse ignorée) est `curl`,
  `wget`, `http`, `https`, `Invoke-WebRequest`, `iwr`, `Invoke-RestMethod`, `irm`, ou `python` /
  `python3` / `uv run python` avec `-c`, et que le segment contient `/api/v1/reglages`.
- Une recherche textuelle (`grep`, `rg`), un `Read` ou un `Glob` qui citent la route passent.
- Le message dit que la route est réservée à l'interface, que le contrôle est lexical, qu'il attrape
  une erreur et non une évasion, et que les bornes du registre restent le vrai plafond.
- Le journal du refus porte le nom de l'outil, jamais la commande.

## Tests (`backend/tests/test_garde_reglages.py`)

- `test_refuses_curl_put_on_the_settings_route`, `..._wget`, `..._invoke_webrequest`,
  `..._invoke_restmethod`, `..._python_dash_c_with_urllib`
- `test_refuses_after_a_separator` : `echo x; curl -X PUT http://127.0.0.1:8100/api/v1/reglages/x`
- `test_allows_curl_on_another_route`
- `test_allows_grep_for_the_settings_route`
- `test_allows_uv_run_pytest_on_the_settings_tests`
- `test_refusal_message_states_the_ceiling`
- `test_refusal_log_holds_the_tool_name_only`
- `test_existing_guard_cases_still_pass` : `test_garde_jetons.py` et `test_garde_coffre.py` inchangés et verts

## Critères d'acceptation

- [ ] Les tests ci-dessus passent
- [ ] Le hook reste branché sur les mêmes rôles que le garde de `.env`

## Ce que ça ne fait pas

Une évasion (`cur""l`, un script écrit puis lancé, un `Origin` forgé par un client HTTP maison) :
la limite est dite dans le message.
