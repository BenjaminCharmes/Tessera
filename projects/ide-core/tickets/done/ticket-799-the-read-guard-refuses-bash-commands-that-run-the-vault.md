---
id: ticket-799
title: "The read guard refuses Bash commands that run the vault"
type: feat
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: ["ticket-798"]
estimated_days: 1
created: 2026-11-05
---

# ticket-799 — Le garde de lecture refuse les commandes Bash qui exécutent le coffre

## Objectif

Le garde d'ADR-053 couvre le coffre comme il couvre `.env` : un agent qui lance `keyring`,
`cmdkey` ou `coffre_cli` est refusé, avec un message qui dit le plafond.

## Contexte

Design §7. Le coffre n'est pas un fichier : `Read`, `Glob` et `Grep` ne l'atteignent pas, seul
`Bash` peut l'exécuter. Ce ticket passe en dernier de la série : un garde mergé plus tôt
refuserait au codeur de lancer `python -m tessera.coffre_cli` pour tester les tickets 797 et 798.

## Ce que le ticket fait

- `backend/src/tessera/services/providers/garde_jetons.py` : un contrôle d'exécution, à côté du
  contrôle de chemin. Refus quand le premier mot d'un segment de commande (séparé comme
  `_COMMANDES`, `.exe` retiré, casse ignorée) est `cmdkey`, `vaultcmd`, `keyring`, `secret-tool`,
  ou `security` suivi d'une sous-commande finissant par `-generic-password` ou
  `-internet-password` ; ou pour `python -m keyring` et `-m tessera.coffre_cli` ; ou quand le texte
  contient `import keyring`, `from keyring`, `Get-StoredCredential`, `CredRead` ou `PasswordVault`.
- Une recherche textuelle, un `grep keyring`, un `Read` d'un fichier qui cite le mot passent.
- `ENV_REFUS` (ou un second message) dit que le coffre n'est pas lisible par un agent, que le
  contrôle est lexical, qu'il attrape une erreur et non une évasion, et que la portée d'un jeton
  reste son vrai plafond.
- Le journal du refus porte le nom de l'outil, jamais la commande.

## Tests (`backend/tests/test_garde_coffre.py`)

- `test_refuses_keyring_cli`, `..._cmdkey`, `..._vaultcmd`, `..._secret_tool`,
  `..._macos_security_find_generic_password`
- `test_refuses_python_dash_c_import_keyring` et `test_refuses_python_dash_m_coffre_cli`
- `test_refuses_a_powershell_credential_read`
- `test_refuses_after_a_separator` : `echo x; keyring get tessera VERCEL_TOKEN`
- `test_allows_grep_for_the_word_keyring` et `test_allows_uv_run_pytest_on_the_vault_tests`
- `test_allows_security_without_a_password_subcommand`
- `test_refusal_message_states_the_ceiling`
- `test_refusal_log_holds_the_tool_name_only`
- `test_existing_env_guard_cases_still_pass` : `backend/tests/test_garde_jetons.py` inchangé et vert.

## Critères d'acceptation

- [x] Les tests ci-dessus passent ; `test_garde_jetons.py` n'est pas modifié
- [x] Le hook reste branché sur les mêmes rôles que le garde de `.env`

## Ce que ça ne fait pas

Une évasion (`__import__('key' + 'ring')`, un script écrit puis lancé) : la limite est dite dans
le message, elle n'est pas corrigée ici.
