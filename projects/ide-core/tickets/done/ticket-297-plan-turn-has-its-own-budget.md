---
agent: codeur
created: 2026-10-01
depends_on: []
estimated_days: 0.5
id: ticket-297
pr_number: null
priority: medium
status: done
title: The plan turn has its own turn budget instead of the reviewer's
type: fix
---

# ticket-297 — Le tour de plan a son propre budget d'actions

## Objectif

Que le tour de plan (`plan: true`, ticket-243) ait assez d'actions pour
rendre un plan, au lieu d'échouer systématiquement.

## Contexte

Le 2026-10-01, le tour de plan a échoué trois fois sur trois (tickets 264,
285 et 280) avec `Reached maximum number of turns (10)`. Le run continue
alors sans plan : on perd un appel, et le ticket prévu pour être planifié ne
l'est pas.

Le plan est un appel en lecture seule, et il reçoit donc
`settings.llm_max_turns_reviewer` (10, `config.py:38`, routé par
`routers/orchestrator.py:161`). Ce plafond est pensé pour le reviewer, qui a
le diff dans son prompt (ticket-199). Le plan, lui, doit lire les services
pour décider d'une approche : dix actions n'y suffisent pas.

## Solution proposée

- Un réglage `llm_max_turns_plan`, de 25 par défaut, lu par le provider du
  tour de plan.
- Le reviewer garde `llm_max_turns_reviewer`.

## Critères d'acceptation

- [ ] `Settings` porte `llm_max_turns_plan`, de 25 par défaut
- [ ] Un test vérifie que le tour de plan est appelé avec
      `llm_max_turns_plan`
- [ ] Un test vérifie que le reviewer est toujours appelé avec
      `llm_max_turns_reviewer`

## Dépendances

Aucune.

## Estimation

0,5 jour.

## Risques

Aucun : le plan reste en lecture seule, seul son budget change.