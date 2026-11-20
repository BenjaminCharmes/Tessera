---
agent: codeur
created: 2026-11-11
depends_on: []
estimated_days: 0.1
id: ticket-926
pr_number: null
priority: low
status: done
title: "The inspirations register records the last reviewed version of each tool"
type: docs
---

# ticket-926 — Le registre des inspirations note la dernière version relue

## Objectif

Que le radar de Vigie ne repropose pas chaque semaine une version déjà relue.

## Contexte

Le radar d'inspirations de Vigie (vigie 074 à 076) compare la dernière
publication d'un outil à la version notée dans `docs/inspirations.md`. Le
ticket-924 a relu humanizer `v4.0.0` et impeccable `skill-v4.8.2` sans rien
reprendre : la « Version reprise » ne bouge pas, et le candidat revenait tous
les dimanches. Vigie 076 lit désormais une ligne facultative « Version
relue » et compare à elle quand elle existe. Fait **à la main**.

## Critères d'acceptation

- [x] `docs/inspirations.md` porte une ligne `Version relue` pour Humanizer
      (`v4.0.0`) et pour Impeccable (`skill-v4.8.2`).
- [x] `test_inspirations.py` passe.
