---
id: ticket-794
title: "A coffre module reads and writes secrets in the system vault"
type: feat
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-05
---

# ticket-794 — Un module `coffre` lit et écrit les secrets dans le coffre du système

## Objectif

Le backend dispose d'une seule porte vers le coffre du système (Gestionnaire d'identification,
Trousseau, Secret Service), derrière un `Protocol` que les tests remplacent.

## Contexte

ADR-073 et `docs/superpowers/specs/2026-11-05-secrets-dans-le-coffre-design.md`, §1 et §2.
Rien ne lit encore le coffre : ce ticket ne change aucun comportement du backend.

## Ce que le ticket fait

- `keyring` en dépendance de `backend/pyproject.toml` (et `backend/uv.lock`).
- `backend/src/tessera/coffre.py` : `SERVICE`, `NOMS_SECRETS` (les neuf noms), `CoffreAbsent`,
  `CoffreEnErreur`, le `Protocol` `Coffre` et `coffre_du_systeme()`, signatures du design.
- `coffre_du_systeme()` lève `CoffreAbsent` pour les backends `fail` et `null` de `keyring` ;
  `ecrire` relit et compare, et lève `CoffreEnErreur` plutôt que tronquer.
- Les erreurs de `keyring` autres que « aucun backend » deviennent `CoffreEnErreur`, sans la
  valeur ni le nom dans le message.

## Tests (`backend/tests/test_coffre.py`)

- `test_noms_secrets_lists_the_nine_names` : la liste est exactement celle du design.
- `test_lire_returns_none_for_a_missing_entry`
- `test_ecrire_then_lire_round_trips` avec un backend `keyring` en mémoire posé par
  `keyring.set_keyring`, restauré après le test.
- `test_ecrire_fails_when_the_vault_returns_another_value` : un backend qui tronque lève
  `CoffreEnErreur`.
- `test_supprimer_missing_entry_is_a_noop`
- `test_presents_only_lists_known_names` : une entrée étrangère du service `tessera` est ignorée.
- `test_coffre_du_systeme_raises_absent_for_the_fail_backend` et `..._for_the_null_backend`.
- `test_a_locked_vault_raises_coffre_en_erreur` : un backend qui lève `KeyringLocked`.
- `test_error_messages_never_hold_a_secret_value`

## Critères d'acceptation

- [x] `backend/src/tessera/coffre.py` expose les noms et signatures du design, sans importer
      `tessera.config`
- [x] Les tests ci-dessus passent sans toucher le vrai coffre de la machine
- [x] `uv sync` réussit avec `keyring` ; sous Smart App Control, ses dépendances Windows sont du
      Python pur (à noter dans le message de commit si ce n'est pas le cas)
- [x] mypy passe sur les deux plateformes (`--platform linux` compris)

## Ce que ça ne fait pas

Aucune lecture par `Settings` (ticket-795), aucune commande (ticket-797).

## Risques

Ce ticket touche `backend/pyproject.toml` : le fichier est nommé ici, pour la porte de
configuration des tests.
