---
id: ticket-199
title: "Le reviewer relit en dix tours d'outils, pas trente"
type: chore
status: done
pr_number: 66
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-09-26
---

# ticket-199 — Le reviewer relit en dix tours d'outils, pas trente

## Objectif

Borner le reviewer à ce qu'une relecture demande : le diff est déjà dans son
prompt, ses outils servent à regarder autour, pas à redécouvrir le dépôt.

## Contexte

Le reviewer reçoit le diff git **complet** dans son prompt (`run_review`)
**et** un provider en lecture (`Read`, `Glob`, `Grep`) avec le même
`max_turns` que le codeur, 30. Sur les runs mesurés, il relit en moyenne
31 k tokens depuis le cache, jusqu'à 124 k, pour 2,9 k produits. Trente tours
pour relire un diff qu'on lui a collé, c'est un budget de codeur donné à un
lecteur.

## Solution proposée

- `config.py` gagne `llm_max_turns_reviewer: int = 10`, documenté dans
  `.env.example`.
- `provider_pour_role` accepte `max_turns` en argument ; les deux fabriques
  de runner (`routers/orchestrator.py`, `routers/agents.py`) le passent pour
  le rôle `reviewer`.
- Le prompt du reviewer dit qu'il a le diff, et que ses outils servent à
  vérifier un contexte, pas à relire le projet.

## Critères d'acceptation

- [ ] Un test vérifie que le provider construit pour `reviewer` porte
      `max_turns == settings.llm_max_turns_reviewer`, et celui du codeur
      `settings.llm_max_turns`
- [ ] `.env.example` décrit `LLM_MAX_TURNS_REVIEWER`
- [ ] `uv run pytest` et `uv run mypy src/` passent

## Ce que ça ne fait pas

Ne retire pas les outils du reviewer ni le diff de son prompt : l'un vérifie
l'autre. Ne touche pas au codeur.

## Dépendances

Aucune.

## Estimation

Une demi-journée.

## Risques

Un reviewer qui atteint dix tours rend son verdict sur ce qu'il a lu ; s'il
refuse à tort faute de contexte, le tour suivant du codeur le dira, et le
réglage se remonte dans `.env`.
