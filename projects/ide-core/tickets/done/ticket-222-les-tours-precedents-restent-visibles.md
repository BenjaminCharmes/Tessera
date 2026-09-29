---
agent: codeur
created: 2026-09-29
depends_on:
- ticket-216
estimated_days: 1
id: ticket-222
pr_number: null
priority: medium
status: done
title: Le panneau Agents garde les tours précédents d'un run
type: feat
---

# ticket-222 — Les tours précédents restent visibles

## Objectif

Quand un run passe au tour 2, l'utilisateur voit encore ce que le codeur a fait et ce que le reviewer a demandé au tour 1.

## Contexte

`streamState` ne garde qu'un bloc par agent. Au tour 2, `agent_started` vide le texte du codeur, et le verdict du reviewer est remplacé par le nouveau (`frontend/src/hooks/streamState.ts`). Pourtant les événements sont tous conservés dans `events`. Or c'est justement le verdict du tour 1 qui explique pourquoi un tour 2 existe.

## Solution proposée

Le panneau devient un **fil chronologique**, comme une conversation : Codeur (tour 1) → Reviewer (tour 1) → Codeur (tour 2) → Reviewer (tour 2)… Chaque passage d'un agent est une entrée qui s'ajoute, et rien n'est écrasé. Les entrées terminées sont repliées, avec leur résumé visible (le verdict pour le reviewer, la première ligne du compte rendu pour le codeur). L'entrée en cours, en bas du fil, reste dépliée. L'état range les passages dans l'ordre des `agent_started`. Frontend uniquement.

## Critères d'acceptation

- [ ] Un test Vitest : après `agent_started` du codeur au tour 2, le verdict du reviewer du tour 1 reste dans l'état
- [ ] Un test Vitest : un run à deux tours rend quatre entrées dans l'ordre codeur, reviewer, codeur, reviewer
- [ ] Un test Vitest : une entrée terminée est repliée et affiche son résumé, et un clic la déplie
- [ ] Un run à un seul tour s'affiche avec ses deux entrées, sans en-tête de tour (test Vitest)

## Dépendances

ticket-216 (le compte rendu du codeur vient de `agent_done`).