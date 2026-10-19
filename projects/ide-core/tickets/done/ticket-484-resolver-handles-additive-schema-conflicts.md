---
agent: codeur
created: 2026-10-16
depends_on: []
estimated_days: 1
id: ticket-484
plan: true
pr_number: null
priority: medium
status: done
title: Additive conflicts in a Prisma schema are resolved mechanically, and colliding
  migration numbers are renumbered
type: feat
---

# ticket-484 — Conflits additifs de schéma Prisma et migrations en collision

## Objectif

Deux tickets qui ajoutent chacun un modèle au même `schema.prisma`, ou chacun
une migration du même numéro, ne bloquent plus la livraison.

## Contexte

Vu deux fois : devinoo (15/10, tickets 002, 003, 005 sur `schema.prisma`,
résolus à la main) et kadoomi (16/10, ticket-011 : « résolveur tenté sur
prisma/schema.prisma, sans succès »). Dans les deux cas, chaque côté ajoutait
un bloc `model` au même endroit : un cas « garder les deux » mécanique, dont
le piège est l'accolade fermante partagée entre les deux blocs. Kadoomi a dû
aussi renuméroter une migration (`0005` pris par le ticket-010, devenu
`0006`).

Le résolveur (`backend/src/tessera/services/resolveur_conflit.py`, prompt
`agents/prompts/resolveur-conflit.md`) traite tout conflit par un agent.

## Solution proposée

1. Avant l'agent, une résolution mécanique pour un fichier `.prisma` : si
   chaque côté d'un conflit n'ajoute que des blocs complets (`model`, `enum`,
   `type`, sans modifier de bloc existant), garder les blocs des deux côtés
   dans l'ordre base puis ticket, en réparant l'accolade partagée. Sinon,
   passer la main au résolveur comme aujourd'hui.
2. Après le rebase, si deux dossiers de `prisma/migrations/` portent le même
   préfixe numérique, renommer celui du ticket au numéro libre suivant et le
   journaliser. Le plan précise comment repérer les migrations quand le
   préfixe est un horodatage plutôt qu'un numéro.

## Critères d'acceptation

- [ ] Un test vérifie que deux ajouts de `model` au même endroit donnent un
      schéma qui contient les deux modèles et aucune marque de conflit
- [ ] Un test vérifie qu'un conflit qui modifie un bloc existant passe
      toujours au résolveur
- [ ] Un test vérifie qu'une migration `0005_x` du ticket en collision avec
      `0005_y` de la base est renommée `0006_x`, avec une ligne de journal
- [ ] Un test vérifie qu'aucun renommage n'a lieu sans collision