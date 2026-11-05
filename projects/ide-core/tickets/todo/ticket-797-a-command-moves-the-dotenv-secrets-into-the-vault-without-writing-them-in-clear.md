---
id: ticket-797
title: "A command moves the dotenv secrets into the vault without writing them in clear"
type: feat
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: ["ticket-795"]
estimated_days: 1
created: 2026-11-05
---

# ticket-797 — Une commande range les secrets de `.env` dans le coffre, sans jamais les écrire en clair

## Objectif

`.\scripts\tessera.ps1 secrets migrer` vide `.env` de ses secrets après les avoir mis dans le
coffre et relus ; `set`, `supprimer` et `lister` complètent le verbe.

## Contexte

Design §5. Un `.env` existant porte aujourd'hui les neuf secrets en clair.

## Ce que le ticket fait

- `backend/src/tessera/coffre_cli.py`, lancé par `python -m tessera.coffre_cli` : `migrer`,
  `set <NOM>` (valeur sur l'entrée standard), `supprimer <NOM>`, `lister` (nom → `coffre`,
  `.env` ou `absent`). Aucune valeur en sortie, en argument ni dans un fichier temporaire.
- `migrer` suit les cinq étapes du §5 : placeholder ignoré, conflit sans écrasement, relecture
  avant tout retrait, ligne remplacée par un commentaire, `SECRETS_SOURCE=coffre` ajouté, `.env`
  réécrit dans un fichier voisin puis `os.replace`, aucune sauvegarde `.env.bak`. Code de sortie
  non nul sur une relecture échouée ou un conflit ; rappel de faire tourner les jetons.
- `scripts/tessera.ps1` : verbe `secrets` avec un sous-verbe (`migrer`, `set`, `supprimer`,
  `lister`) ; `set` demande la valeur par `Read-Host -AsSecureString` et la passe par l'entrée
  standard. `help` le décrit.

## Tests (`backend/tests/test_coffre_cli.py`, coffre en mémoire, `.env` dans `tmp_path`)

- `test_migrer_moves_a_secret_and_replaces_its_line_by_a_comment`
- `test_migrer_keeps_comments_and_other_settings_untouched`
- `test_migrer_skips_empty_and_placeholder_values`
- `test_migrer_does_not_overwrite_a_different_vault_value` : ligne conservée, sortie non nulle.
- `test_migrer_keeps_the_line_when_the_readback_differs`
- `test_migrer_is_idempotent` et `test_migrer_resumes_after_an_interruption`
- `test_migrer_adds_secrets_source_once`
- `test_migrer_leaves_no_backup_and_no_temp_file`
- `test_no_subcommand_output_contains_a_secret_value` : sur `migrer`, `set`, `lister`.
- `test_set_reads_the_value_from_stdin_only`
- `test_lister_reports_where_each_name_lives`
- `test_migrer_refuses_when_the_vault_is_absent`
- `test_tessera_ps1_lists_the_secrets_verb` : le script contient le verbe et son sous-verbe.

## Critères d'acceptation

- [ ] Les tests ci-dessus passent
- [ ] Une migration réelle à la main sur un `.env` jetable (valeurs factices) relit le coffre, vide
      le fichier et laisse `make dev` démarrer ; noter le résultat dans le message de commit
- [ ] `.env` du dépôt n'est jamais lu ni modifié par les tests

## Ce que ça ne fait pas

La sous-commande `termes` (ticket-798). La rotation des jetons déjà passés en clair : une action
de l'utilisateur.
