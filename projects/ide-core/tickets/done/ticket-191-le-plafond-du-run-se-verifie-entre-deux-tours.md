---
id: ticket-191
title: "Le plafond de dépense d'un run se vérifie entre deux tours"
type: fix
status: done
pr_number: 53
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-09-26
---

# ticket-191 — Le plafond de dépense d'un run se vérifie entre deux tours

## Objectif

Qu'un ticket seul ne puisse pas dépasser `RUN_MAX_BUDGET_USD`.

## Contexte

`budget_exhausted()` (`services/orchestrator.py:116`) n'est appelé qu'entre
deux tickets (`:329`, `:392`). À l'intérieur d'un ticket, la seule borne est
`llm_max_budget_usd` = 2 $ **par appel**. Avec trois tours de codeur et de
reviewer, un ticket peut atteindre 12 $ sans qu'aucun plafond de run ne
bouge, alors que `run_max_budget_usd` vaut 5 $.

ADR-020 place la vérification entre deux tickets pour ne pas laisser de
travail non commité. Une frontière de tour a la même propriété : le codeur a
fini d'écrire, et le run commite à toute sortie (ADR-038).

## Solution proposée

- Dans la boucle `for round in 1..max_review_rounds` de `run_pipeline`,
  vérifier `budget_exhausted()` avant de lancer un tour N > 1.
- Si le plafond est atteint : sortir en `blocked`, commiter en
  `unapproved work` comme le fait `finish_rounds_exhausted`, et remplir
  `arret` avec le montant dépensé et le plafond — la même phrase que
  l'événement `run_budget_exhausted` entre tickets.
- Un tour 1 démarre toujours, même sous plafond : refuser de commencer un
  ticket est le rôle de la vérification entre tickets, pas de celle-ci.

## Critères d'acceptation

- [ ] Un test vérifie qu'un run dont le tour 1 dépasse le plafond ne lance
      pas le tour 2, termine en `blocked`, et porte le montant dans `arret`
- [ ] Un test vérifie que le travail du tour 1 est commité en
      `unapproved work` dans ce cas
- [ ] Un test vérifie qu'un plafond à 0 ne borne rien, comme aujourd'hui
- [ ] `uv run pytest` et `uv run mypy src/` passent

## Ce que ça ne fait pas

Ne change pas les valeurs des plafonds, ni la vérification entre tickets.

## Dépendances

Aucune.

## Estimation

Une demi-journée.

## Risques

Aucun notable : le chemin `blocked` avec commit existe déjà.
