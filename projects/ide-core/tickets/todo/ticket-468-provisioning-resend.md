---
agent: codeur
created: 2026-10-16
depends_on:
- ticket-466
estimated_days: 1
id: ticket-468
priority: medium
status: todo
title: The Resend steps find or create the sending domain and a dedicated key, then
  verify the domain once its DNS records are published
type: feat
---

# ticket-468 — Étapes Resend : domaine, clé d'envoi, vérification

## Objectif

Qu'un projet en ligne puisse envoyer des e-mails depuis son domaine : domaine
créé, clé d'envoi propre au projet dans Vercel, vérification relancée une fois
le DNS publié.

## Contexte

ADR-053. L'API Resend rend les enregistrements DNS à la création du domaine ;
la vérification est asynchrone (`POST /domains/{id}/verify`) et le domaine reste
`pending` le temps de la propagation. Une clé d'API n'est montrée qu'à sa
création : trouvée sans sa variable Vercel, sa valeur est perdue. Relire la
documentation de l'API Resend (domaines, clés) et citer les pages dans la
docstring.

## Solution proposée

- `ResendClient` (`services/provisioning/resend.py`), mêmes règles de logs et
  d'erreurs que les autres clients.
- Étape `resend_domain` : domaine cherché par nom, créé sinon ; ses
  enregistrements vont dans `ctx.wanted_dns`. Clé d'envoi nommée d'après le
  projet, limitée à l'envoi sur ce domaine, valeur écrite dans Vercel
  (`RESEND_API_KEY`).
- Étape `resend_verify` (après les DNS) : lance la vérification seulement si
  `ctx.dns_published` ; `verified` → `done`, en attente → `pending`, `failed`
  → `failed`.

## Critères d'acceptation

- [ ] Un test vérifie qu'un domaine existant n'est pas recréé, et qu'un domaine
      absent est créé avec ses enregistrements DNS versés dans `ctx.wanted_dns`
- [ ] Un test vérifie que la clé créée est limitée à l'envoi sur le domaine et
      que sa valeur est écrite dans Vercel sous `RESEND_API_KEY`
- [ ] Un test vérifie qu'une clé existante sans `RESEND_API_KEY` dans Vercel
      rend `needs_human`, nomme la clé à supprimer, et n'émet aucun appel de
      suppression
- [ ] Un test vérifie qu'une clé existante avec sa variable rend `skipped`
- [ ] Un test vérifie que la vérification n'est pas lancée tant que
      `ctx.dns_published` est faux, et que les statuts `verified`, en attente et
      `failed` rendent respectivement `done`, `pending`, `failed`

## Ce que ça ne fait pas

Ne supprime aucune clé, ne choisit pas l'adresse d'expédition
(`RESEND_FROM_EMAIL` reste au projet).

## Dépendances

ticket-466 (`env_writer`). Les enregistrements sont publiés par le ticket-469.
