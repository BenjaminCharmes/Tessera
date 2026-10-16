---
agent: codeur
created: 2026-10-16
depends_on: []
estimated_days: 0.25
id: ticket-487
pr_number: null
priority: high
status: done
title: A configuration error names the faulty variable but never echoes its value
type: fix
---

# ticket-487 — Une erreur de configuration ne recopie jamais une valeur

## Objectif

Quand le `.env` de Tessera contient une variable inconnue ou invalide, le
message d'erreur nomme la variable et dit quoi faire, sans jamais afficher sa
valeur.

## Contexte

16/10 : une clé Stripe `sk_test_…` ajoutée au `.env` sous un nom que
`Settings` ne connaît pas (`STRIPE_SECRET_KEY`) a fait lever à pydantic
« Extra inputs are not permitted » avec `input_value='sk_test_51…'` : une
partie de la clé s'est retrouvée dans la sortie. Au démarrage du backend, la
même erreur part dans les logs, et le backend ne démarre pas.

`backend/src/tessera/config.py` déclare
`SettingsConfigDict(env_file=…, env_file_encoding="utf-8")`, sans
`hide_input_in_errors`.

## Solution proposée

- `hide_input_in_errors=True` dans la configuration de `Settings`.
- Au démarrage, une erreur de validation de `Settings` est reformulée :
  « variable inconnue dans .env : STRIPE_SECRET_KEY (à retirer, ou à
  renommer si c'est un jeton de mise en ligne) ». Le nom seulement.
- Le comportement sur une variable inconnue (refus) ne change pas.

## Critères d'acceptation

- [x] Un test vérifie que l'erreur levée pour une variable inconnue de
      valeur `sk_test_secret123` ne contient pas `secret123`
- [x] Un test vérifie que le message reformulé contient le nom de la variable
- [x] Un test vérifie qu'une valeur invalide d'une variable connue n'est pas
      recopiée non plus