---
id: ticket-023
title: "Agent conversationnel agent-creator (backend)"
type: feat
status: done
priority: high
agent: codeur
depends_on:
  - ticket-021
  - ticket-022
estimated_days: 1
created: 2026-06-21
---

# ticket-023 — Agent conversationnel agent-creator

## Objectif

Permettre à un utilisateur de créer un agent personnalisé en langage naturel via une conversation multi-tour. L'IA pose des questions si la description est vague, puis génère automatiquement un system prompt adapté et l'enregistre.

## Contexte

Avec ticket-022, on peut créer un agent en envoyant directement un `role` + `system_prompt`. Mais l'utilisateur moyen ne sait pas écrire un bon system prompt. Ce ticket a créé l'agent `agent-creator` qui dialogue avec l'utilisateur et génère le prompt optimisé.

## Solution implémentée

- **`agents/prompts/agent-creator.md`** — system prompt de l'agent créateur
- **`backend/src/vibe_ide/services/agent_creator.py`** — `AgentCreatorService` conversationnel
- **`POST /api/v1/agents/create-agent`** — endpoint multi-tour

Réponse créée (`created: true`) ou clarification (`created: false, message: "..."`).

## Critères d'acceptation

- [x] Une description précise → agent créé en 1 tour
- [x] Une description vague → question de clarification retournée
- [x] La conversation complète est transmise à Claude à chaque tour
- [x] L'agent créé est immédiatement utilisable via `GET /agents/registry`

## Dépendances

- **ticket-021** — `AgentRegistryService` pour persister l'agent créé.
- **ticket-022** — L'endpoint monte dans le même router agents.

## Estimation

**1j** (réalisé)
