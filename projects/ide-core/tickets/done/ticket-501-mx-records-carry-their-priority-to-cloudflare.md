---
id: ticket-501
title: "An MX record published to Cloudflare carries its priority"
type: fix
status: done
pr_number: null
priority: critical
agent: codeur
depends_on: []
estimated_days: 0.1
created: 2026-10-18
---

# ticket-501 — Un MX publié chez Cloudflare porte sa priorité

## Objectif

L'étape DNS de la mise en ligne publie l'enregistrement MX que Resend demande
(`send.<domaine>`) sans que Cloudflare le refuse.

## Contexte

18/10, mise en ligne de Kadoomi : Cloudflare a répondu 400 au troisième
`POST /zones/<id>/dns_records`, l'enregistrement MX `send.kadoomi.com`.
`DnsRecord.priority` vaut bien 10 (lu chez Resend par `resend_records.py`),
mais `CloudflareClient.create_record` n'envoie que `type`, `name`, `content`,
`ttl` et `proxied`. Cloudflare exige `priority` pour un MX. L'étape s'arrête,
et derrière elle la vérification Resend et le premier déploiement.

Fait à la main (et non par le pipeline) : la correction tient en une ligne et
bloque une mise en ligne en cours.

## Solution

`create_record` ajoute `priority` au corps quand l'enregistrement en a une.

## Critères d'acceptation

- [x] Un test de `tests/test_provisioning_cloudflare.py` vérifie qu'un MX
      créé porte sa priorité dans le corps envoyé
- [x] Un test vérifie qu'un enregistrement sans priorité (A, TXT) n'envoie pas
      de champ `priority`
