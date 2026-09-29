---
agent: codeur
created: 2026-09-29
depends_on:
- ticket-223
- ticket-224
estimated_days: 1
id: ticket-225
pr_number: null
priority: medium
status: done
title: 'Le chat s''organise par conversation : liste, nouvelle, reprise'
type: feat
---

# ticket-225 — Le chat par conversation

## Objectif

Dans la vue Chat, l'utilisateur voit ses conversations, en ouvre une nouvelle, et reprend une ancienne, comme dans l'extension VS Code.

## Contexte

`useChat` accepte un `conversationId`, mais `ChatPanel` passe toujours `"default"`. Toutes les discussions d'un projet s'empilent donc dans une seule conversation, et le plafond de dépense par conversation (`chat_max_conversation_usd`) finit par la bloquer.

## Solution proposée

Une liste à gauche de la vue Chat, alimentée par `GET /{project_id}/chat` (ticket-224). Un bouton « Nouvelle conversation » génère un identifiant neuf, et un clic sur une entrée change le `conversationId` passé à `useChat`. Frontend uniquement.

## Critères d'acceptation

- [ ] Un test Vitest : la vue Chat affiche les conversations rendues par l'API, avec leur titre
- [ ] Un test Vitest : « Nouvelle conversation » ouvre une conversation vide avec un identifiant différent de `default`
- [ ] Un test Vitest : cliquer sur une conversation charge son historique via `api.chat.history` avec son identifiant
- [ ] La conversation `default` existante reste accessible dans la liste (test Vitest)

## Dépendances

ticket-223 (vue Chat), ticket-224 (liste des conversations).