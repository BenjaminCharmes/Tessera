---
agent: codeur
created: 2026-09-29
depends_on: []
estimated_days: 0.5
id: ticket-224
pr_number: null
priority: medium
status: done
title: Le backend liste les conversations du chat d'un projet
type: feat
---

# ticket-224 — Lister les conversations du chat

## Objectif

L'UI peut afficher la liste des conversations d'un projet, avec un titre et une date pour chacune.

## Contexte

`chat_messages` a une colonne `conversation_id`, et `GET /{project_id}/chat/{conversation_id}` rend l'historique d'une conversation. Mais aucune route ne dit quelles conversations existent, alors le frontend utilise toujours `"default"`.

## Solution proposée

`GET /api/v1/projects/{project_id}/chat` rend `[{conversation_id, titre, derniere_activite, messages}]`, trié de la plus récente à la plus ancienne. Le titre est le premier message utilisateur, coupé à 60 caractères. Backend uniquement.

## Critères d'acceptation

- [ ] Un test : deux conversations enregistrées → la route rend deux entrées, la plus récente en premier
- [ ] Un test : le titre est le premier message `user` de la conversation, coupé à 60 caractères
- [ ] Un test : un projet sans message rend une liste vide, pas une erreur
- [ ] La route existante `GET /{project_id}/chat/{conversation_id}` garde son comportement (test existant vert)

## Dépendances

Aucune.