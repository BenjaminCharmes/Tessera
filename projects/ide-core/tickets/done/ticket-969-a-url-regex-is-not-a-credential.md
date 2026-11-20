---
agent: codeur
created: 2026-11-13
depends_on: []
id: ticket-969
priority: medium
status: done
title: "A regular expression matching URLs is not taken for credentials in a URL"
type: fix
---

# ticket-969 — Une regex d'URL n'est pas prise pour des identifiants dans une URL

## Contexte

Signalement de la session RepoHealth (13/11) : la livraison de repo-health
ticket-064, approuvé, a été bloquée par le motif `url-credentials`
(`services/gardes/secrets_diff.py`) sur une regex Python,
`r"^(?:https?://(?:[^@/]+@)?github\.com/|…"`. La partie utilisateur du motif
acceptait tout sauf quelques caractères : `(?` puis `:` puis `[^` puis `@`
formaient un « utilisateur:mot de passe@ ».

## Correctif

La partie utilisateur ne prend plus que les caractères d'une URL
(`[A-Za-z0-9._%~+-]`). Le mot de passe garde sa règle.

## Critères d'acceptation

- [x] Un test : la ligne de repo-health n'est plus signalée.
- [x] Les tests existants du contrôle des secrets passent sans changement
      (dont `postgres://admin:hunter2@…`, toujours signalé).

## Ce que ça ne fait pas

- Fait à la main : un motif.
