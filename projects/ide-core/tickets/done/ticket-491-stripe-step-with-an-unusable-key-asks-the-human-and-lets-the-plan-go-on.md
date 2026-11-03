---
agent: codeur
created: 2026-10-16
depends_on: []
estimated_days: 0.5
id: ticket-491
pr_number: 514
priority: high
status: done
title: The Stripe step with a key of the wrong type asks the human and lets the rest
  of the plan run
type: fix
---

# ticket-491 — Une clé Stripe du mauvais type ne bloque pas le reste de la mise en ligne

## Objectif

Une clé Stripe inutilisable arrête l'étape Stripe, pas la mise en ligne.

## Contexte

16/10, première relance de la mise en ligne de devinoo après le ticket-488 :
`STRIPE_API_KEY` contenait la clé **publiable** (`pk_test_…`), pas une clé
restreinte. `StripeClient.key_mode` a rendu `unknown`, et `StripeStep`
(`backend/src/tessera/services/provisioning/stripe_step.py`) a rendu `failed`
avec « STRIPE_API_KEY is neither a test nor a live key ». Le plan s'est arrêté
là : `dns`, `resend_verify` et `redeploy` n'ont pas tourné, et le domaine
Resend créé à l'étape précédente est resté `not_started`, sans ses
enregistrements DNS. Une clé absente aurait donné `needs_human` et laissé le
plan continuer : une clé du mauvais type doit faire pareil.

## Solution proposée

- `key_mode == "unknown"` rend `needs_human`, pas `failed`, avec un message qui
  dit ce qui est attendu : une clé restreinte de test (`rk_test_…`) ou secrète
  (`sk_test_…`), créée dans Stripe → Developers → API keys, et que `pk_` est la
  clé publiable, qui ne sert qu'au navigateur. La valeur n'apparaît jamais.
- Le message rappelle que la clé n'est relue qu'au redémarrage du backend.

## Ce que ça ne fait pas

- Ne change pas la règle « un `failed` arrête le plan » : une erreur réseau
  ou une réponse Stripe inattendue reste `failed`.

## Critères d'acceptation

- [ ] Un test vérifie qu'une clé `pk_test_…` rend `needs_human` avec un
      message qui nomme `rk_test_` et `pk_`, sans la valeur de la clé
- [ ] Un test vérifie que les étapes suivantes du plan tournent après ce
      `needs_human`
- [ ] Un test vérifie qu'une clé absente rend toujours `needs_human` et qu'une
      erreur réseau rend toujours `failed`