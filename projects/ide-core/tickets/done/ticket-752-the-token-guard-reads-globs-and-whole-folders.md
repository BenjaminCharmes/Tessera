---
agent: codeur
created: 2026-11-03
depends_on: []
estimated_days: 1
id: ticket-752
pr_number: null
priority: medium
status: done
title: The token guard reads globs and whole folders that reach Tessera's .env
type: fix
---

# ticket-752 — Le garde-jetons lit les globs et les dossiers entiers qui atteignent le `.env` de Tessera

## Objectif

Une lecture par glob ou par dossier entier qui atteindrait le `.env` de Tessera est
refusée comme la lecture nommée.

## Contexte

C-08 de `docs/audit/securite.md` (S-13), jamais ticketée.
`backend/src/tessera/services/garde_jetons.py` ne refuse en Bash qu'un jeton dont le
dernier segment est exactement `.env` : `cat ../../.e*`, `cat ../../.en?` passent, comme
`grep -r motif ../..`. L'outil `Grep` avec un `path` de dossier et sans `glob` rend faux.
ADR-053 : un agent ne lit pas ce fichier.

## Critères d'acceptation

- [ ] `test_bash_glob_reaching_the_env_is_refused` : `cat <racine tessera>/.e*` et `.en?` sont
      refusés
- [ ] `test_grep_on_a_directory_holding_the_env_is_refused` : `grep -r x <racine tessera>` et
      l'outil `Grep` sur ce dossier sans `glob` sont refusés
- [ ] `test_listing_a_folder_still_passes` : `ls <racine tessera>` et `Grep` sur
      `backend/src` passent