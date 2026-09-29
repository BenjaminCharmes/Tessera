---
id: ticket-227
title: "Le verdict du reviewer tient sur une ligne avec son icône"
type: fix
status: done
pr_number: null
priority: low
agent: codeur
depends_on: []
estimated_days: 0.1
created: 2026-09-29
---

# ticket-227 — Le verdict tient sur une ligne

## Objectif

« ⚠ CHANGES_REQUESTED » et « ✓ APPROVED » s'affichent sur une seule ligne dans le panneau Agents.

## Contexte

Dans `VerdictBanner`, l'icône SVG et le mot étaient dans un `div` en affichage bloc. L'icône occupait donc sa propre ligne et le verdict passait en dessous.

## Solution

L'en-tête devient `flex items-center gap-1`.

## Critères d'acceptation

- [x] Un test Vitest : l'en-tête du verdict porte `flex` et `items-center`, et contient l'icône
