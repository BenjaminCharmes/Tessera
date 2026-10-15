---
id: ticket-455
title: "The queue log says a PR is handed to the CI watcher only when it is"
type: fix
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.5
plan: true
created: 2026-10-15
---

# ticket-455 — « Confiée au CIWatcher » ne s'écrit que si le watcher a la PR

## Objectif

La ligne « PR #N confiée au CIWatcher » du journal de file n'est écrite que
lorsque `surveiller` a réellement été appelé pour cette PR.

## Contexte

Mis au jour en établissant où la PR #14 de make-your-call était restée
(ticket-452). La boucle de file (`backend/src/tessera/services/orchestrator.py`,
autour de la ligne 675) écrit cette ligne dès que la livraison porte un
`pr_number`. Or `surveiller` n'est appelé que si l'`arret` est nul ou si la PR
est orpheline (même fichier, autour de la ligne 261) : une PR ouverte après un
conflit résolu (ADR-033) n'est jamais confiée au watcher, et la ligne l'affirme
pourtant. Elle a fait croire pendant une demi-heure que #14 était surveillée.

## Solution proposée

- Écrire « confiée au CIWatcher » seulement pour une PR dont `surveiller` a
  été appelé.
- Pour une PR laissée ouverte à relire (conflit résolu), écrire une ligne qui
  le dit : « PR #N ouverte, à relire : non confiée au CIWatcher ».

## Critères d'acceptation

- [ ] Un test vérifie qu'une livraison avec `pr_number` et un `arret` de
      conflit résolu n'écrit pas « confiée au CIWatcher »
- [ ] Un test vérifie qu'une PR sans conflit, surveillée, l'écrit toujours

## Ce que ça ne fait pas

- Ne change pas la décision de ne pas surveiller (ni merger) une PR issue d'un
  conflit résolu : c'est ADR-033.
- Ne corrige pas l'attente d'une dépendance : c'est ticket-451.
