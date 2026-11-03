---
agent: codeur
created: 2026-10-16
depends_on:
- ticket-465
estimated_days: 1
id: ticket-469
pr_number: 491
priority: medium
status: done
title: The DNS step publishes the records other steps asked for in the Cloudflare
  zone, never overwriting or deleting one
type: feat
---

# ticket-469 — Étape DNS (Cloudflare)

## Objectif

Publier dans la zone Cloudflare les enregistrements que Vercel et Resend
demandent, et dire à l'utilisateur ceux qu'il doit poser lui-même quand Tessera
ne le peut pas.

## Contexte

ADR-053. Le jeton Cloudflare est limité à `Zone.DNS` en édition sur la seule
zone du projet ; l'achat du domaine et son ajout à Cloudflare restent humains.
Les enregistrements sont publics : leur nom, type et contenu peuvent apparaître
dans un événement. Relire la documentation de l'API Cloudflare (zones,
enregistrements DNS) et citer les pages dans la docstring. L'hypothèse retenue :
les enregistrements vers Vercel sont créés en DNS seul (non proxifiés).

## Solution proposée

- `CloudflareClient` (`services/provisioning/cloudflare.py`).
- Étape `dns` : zone cherchée par `online.domain` ; pour chaque
  enregistrement de `ctx.wanted_dns`, créé s'il n'existe pas à l'identique
  (type, nom, contenu). Elle met `ctx.dns_published` à vrai quand tout est en
  place.
- Même type et même nom avec un autre contenu : `needs_human`, rien n'est
  écrasé. L'étape ne supprime jamais.
- `dns` absent de `online.resources`, ou jeton absent : `manual`, avec la liste
  des enregistrements à poser.

## Critères d'acceptation

- [ ] Un test vérifie qu'une zone absente de Cloudflare rend `needs_human`
      sans rien créer
- [ ] Un test vérifie qu'un enregistrement identique existant est ignoré et
      qu'un enregistrement manquant est créé non proxifié
- [ ] Un test vérifie qu'un enregistrement de même type et même nom mais de
      contenu différent rend `needs_human`, sans écriture ni suppression
- [ ] Un test vérifie qu'aucun appel de suppression n'est jamais émis
- [ ] Un test vérifie que sans `CLOUDFLARE_API_TOKEN`, ou `dns` non déclaré,
      l'étape rend `manual` avec la liste des enregistrements dans `detail`
- [ ] Un test vérifie que `ctx.dns_published` n'est vrai que quand tous les
      enregistrements demandés existent

## Ce que ça ne fait pas

N'achète pas de domaine, ne crée pas de zone, ne modifie pas les
enregistrements que Tessera n'a pas demandés.

## Dépendances

ticket-465.