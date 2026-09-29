---
id: ticket-222
title: "Le panneau Agents garde les tours précédents d'un run"
type: feat
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: ["ticket-216"]
estimated_days: 1
created: 2026-09-29
---

# ticket-222 — Les tours précédents restent visibles

## Objectif

Quand un run passe au tour 2, l'utilisateur voit encore ce que le codeur a fait et ce que le reviewer a demandé au tour 1.

## Contexte

`streamState` ne garde qu'un bloc par agent. Au tour 2, `agent_started` vide le texte du codeur, et le verdict du reviewer est remplacé par le nouveau (`frontend/src/hooks/streamState.ts`). Pourtant les événements sont tous conservés dans `events`. Or c'est justement le verdict du tour 1 qui explique pourquoi un tour 2 existe.

## Solution proposée

L'état range les blocs par tour. Le panneau affiche le tour en cours déplié, et chaque tour précédent replié sous « Tour N », avec le verdict du reviewer en tête. Frontend uniquement.

## Critères d'acceptation

- [ ] Un test Vitest : après `agent_started` au tour 2, le verdict du reviewer du tour 1 reste dans l'état
- [ ] Un test Vitest : le panneau rend un en-tête « Tour 1 » replié et le tour 2 déplié
- [ ] Un test Vitest : déplier « Tour 1 » affiche le compte rendu du codeur de ce tour
- [ ] Un run à un seul tour s'affiche comme aujourd'hui, sans en-tête de tour (test Vitest)

## Dépendances

ticket-216 (le compte rendu du codeur vient de `agent_done`).
