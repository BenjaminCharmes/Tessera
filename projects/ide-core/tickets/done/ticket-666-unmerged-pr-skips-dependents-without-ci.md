---
id: ticket-666
title: "Under merge_without_ci, an unmerged PR skips its dependents instead of letting them start"
type: fix
status: done
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-10-29
---

# ticket-666 — Sans CI aussi, une PR non mergée retire ses dépendants

## Objectif
Qu'un ticket ne démarre jamais sans le code d'un ticket dont il dépend et qui n'est
pas mergé, quel que soit le mode de merge du projet.

## Contexte
Signalé le 29/10 par la session Curio (run 24211ab8). La livraison de ticket-021
s'est arrêtée sur un `ReadTimeout`, et sa PR #39 est restée ouverte, non mergée.
Pourtant, ticket-022, qui porte `depends_on: [ticket-021]`, a démarré six secondes
plus tard.

Curio est en `merge_without_ci`. Dans ce mode, `run_queue` attend le merge avant
chaque ticket suivant par `_attendre_merge_et_syncer`, qui ne rendait rien : la
file repartait donc sans retirer les dépendants. Hors de ce mode, une PR non
mergée les retire (ADR-060, ticket-569).

## Solution proposée
`_attendre_merge_et_syncer` rend vrai seulement quand la PR est mergée ; un délai
dépassé compte comme non mergé. Non mergée, la PR retire ses dépendants par
`sauter_dependants`, comme dans l'autre mode, et la file s'arrête s'il ne reste rien.

## Critères d'acceptation
- [x] Un test vérifie qu'en `merge_without_ci`, une PR non mergée fait sauter son dépendant, journalisé « sauté : dépend de …, non mergé », et que l'indépendant démarre

## Ce que ça ne fait pas
- Ne change pas l'attente du merge avant chaque ticket propre à ce mode.
