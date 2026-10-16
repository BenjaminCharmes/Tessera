---
agent: codeur
created: 2026-10-16
depends_on:
- ticket-466
estimated_days: 1.5
id: ticket-470
pr_number: 493
priority: medium
status: done
title: The Stripe step works in test mode unless the project declares live, and finds
  or creates the product, price and webhook
type: feat
---

# ticket-470 — Étape Stripe : produit, prix, webhook

## Objectif

Que le webhook d'un projet existe et que son secret soit dans Vercel, avec en
option un produit et un prix, **en mode test** tant que rien d'explicite ne dit
le contraire.

## Contexte

ADR-053. Le défaut protège, le cas particulier s'énonce : une clé `live` n'est
acceptée que si `online.stripe.mode` vaut `"live"` dans `agents.json`, que les
agents ne peuvent pas écrire (ADR-027). L'API Stripe ne crée pas de clé d'API :
`STRIPE_SECRET_KEY` **du site** se pose à la main dans Vercel ; l'étape en
vérifie le nom. Un prix Stripe est immuable : un prix existant n'est jamais
modifié. Relire la documentation de l'API Stripe (produits, prix, webhook
endpoints, clés restreintes) et citer les pages dans la docstring.

## Solution proposée

- `StripeClient` (`services/provisioning/stripe_step.py` — le nom évite
  d'ombrer le SDK s'il est un jour ajouté ; `httpx`, pas de SDK).
- Déclaration (`OnlineConfig.stripe`) : `webhook_path` et `events`
  obligatoires ; `product` et `price_cents` facultatifs ; `mode` vaut `test`
  par défaut.
- Produit trouvé par `metadata[tessera_project]`, prix par `lookup_key`, webhook
  par URL (`https://<domain><webhook_path>`) ; le secret rendu à la création du
  webhook va dans Vercel (`STRIPE_WEBHOOK_SECRET`).
- `STRIPE_SECRET_KEY` absent de Vercel : `needs_human`, avec l'instruction de
  créer une clé restreinte du site.

## Critères d'acceptation

- [ ] Un test vérifie qu'une clé `live` avec un `mode` absent ou `test` rend
      `failed` sans aucune requête, et qu'elle passe avec `"mode": "live"`
- [ ] Un test vérifie que produit et prix existants (trouvés par métadonnée et
      `lookup_key`) ne sont pas recréés ni modifiés, et que produit et prix ne
      sont créés que s'ils sont déclarés
- [ ] Un test vérifie qu'un webhook absent est créé avec les `events` déclarés
      et que son secret est écrit dans Vercel sous `STRIPE_WEBHOOK_SECRET`
- [ ] Un test vérifie qu'un webhook existant sans sa variable rend
      `needs_human`, nomme le webhook, et n'émet aucune suppression
- [ ] Un test vérifie que l'absence de `STRIPE_SECRET_KEY` dans Vercel rend
      `needs_human` sans rien écrire
- [ ] Un test vérifie que la clé et le secret du webhook n'apparaissent ni dans
      les logs, ni dans les événements, ni dans une `ServiceError`

## Ce que ça ne fait pas

N'active pas le mode réel, ne crée pas de code promo (ils se créent dans le
tableau de bord Stripe, sans déploiement), ne supprime rien.

## Dépendances

ticket-466 (`env_writer`).