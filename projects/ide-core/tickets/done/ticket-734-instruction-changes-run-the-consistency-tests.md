---
id: ticket-734
title: "An instruction-only diff runs the consistency tests"
type: fix
status: done
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-02
---

# ticket-734 — Un diff de consignes lance les tests de cohérence

## Objectif
Qu'un ticket qui ne touche que des consignes (ADR, contraintes, `CLAUDE.md`, prompts,
skills) ne passe plus le testeur sans aucun test.

## Contexte
Le 02/11, le ticket-674 (type `design`) a écrit l'ADR-069 (167 mots pour 160) et une règle
qui portait `contraintes.md` à 12 064 caractères pour 12 000 : approuvé, puis CI rouge sur
`test_consignes_coherentes.py`. `scripts/verifier.py` (`chains_for`) ne lance rien quand le
diff ne touche ni `backend/` ni `frontend/`. Fait à la main : le script que lance le
testeur se refuse en écriture aux agents (ADR-027).

## Critères d'acceptation
- [x] `consignes_touchees` reconnaît `projects/ide-core/memory/`, `agents/prompts/`,
      `.claude/skills/` et tout `CLAUDE.md` ; testé dans `test_verifier.py`
- [x] Un diff de consignes seul lance `CONSIGNES_STEPS` (`test_consignes_coherentes.py`) ; testé
