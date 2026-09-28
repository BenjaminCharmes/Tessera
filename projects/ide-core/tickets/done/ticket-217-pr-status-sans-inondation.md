---
id: ticket-217
title: "Le statut de PR d'une carte ne réessaie plus une PR introuvable"
type: fix
status: done
pr_number: null
priority: critical
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-28
---

# ticket-217 — Le statut de PR sans inondation

## Objectif

Une carte du Kanban cesse d'interroger GitHub quand sa PR n'existe pas, et les tickets d'`ide-core` ne portent plus de numéros de PR venus d'un autre dépôt.

## Contexte

Depuis le ticket-212, `ide-core` a un `github_remote`. Chaque carte qui porte un `pr_number` appelle alors `GET …/pr-status` au montage, puis toutes les 30 secondes, jusqu'à ce que la PR soit `merged` ou `closed`. Sur 106 cartes, 61 portaient un numéro de l'ancien dépôt, antérieur à la réécriture de l'historique : 51 PR inexistantes, et 10 numéros réattribués depuis à la PR d'un autre ticket. GitHub répondait 404, la route le laissait remonter en 500, et la carte ignorait l'erreur et réessayait indéfiniment.

Résultat : environ 12 000 appels GitHub par heure pour un quota de 5 000, et des connexions du navigateur saturées. Le panneau Pipeline restait vide, parce que sa requête attendait derrière toutes les autres.

Ce correctif a été fait hors pipeline : lancer le run obligeait à ouvrir `ide-core`, donc à relancer l'inondation.

## Solution

- `GET …/pr-status` : un 404 de GitHub devient un 404 dont le message nomme la PR et le dépôt.
- `TicketCard` : une erreur 4xx arrête le polling de la carte, alors qu'une erreur 5xx le laisse continuer.
- Les 61 `pr_number` qui ne désignent pas une PR du dépôt actuel au nom du ticket (titre ou branche) passent à `null`.

## Critères d'acceptation

- [x] Un test : GitHub répond 404 → la route rend 404 avec `#<numéro>` dans le détail
- [x] Un test Vitest : une réponse `API 404` → un seul appel en 5 minutes
- [x] Un test Vitest : une réponse `API 502` → le polling continue
- [x] Aucun ticket d'`ide-core` ne porte un `pr_number` absent du dépôt actuel ou attribué à un autre ticket
- [x] `uv run pytest` et `npm run test` passent

## Ce que ça ne fait pas

- Une erreur 403 ou 429 de GitHub (quota épuisé) remonte encore en 500, et le polling continue. C'est le bon comportement pour une panne passagère, mais pas pour un quota épuisé pendant une heure.
- Les autres projets n'ont pas été vérifiés : leurs numéros viennent de leur propre dépôt et n'ont pas subi de réécriture d'historique.
