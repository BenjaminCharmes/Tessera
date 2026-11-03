---
id: ticket-709
title: "Rules and instruction files say what the code does"
type: docs
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-30
---

# ticket-709 — Les règles et les consignes disent ce que fait le code

## Objectif
Corriger les écarts relevés par `docs/audit/regles.md` (C8, C9, C12) et
`docs/audit/adr.md` (C5, C6) entre `contraintes.md`, les consignes et le code.

**Ce ticket autorise la modification de `CLAUDE.md` (racine et
`projects/ide-core/`) et des skills `write-adr` et `code-review`** (règle 5).
Fait à la main : un agent ne peut écrire ni dans ces fichiers ni hors de
`## Proposées` (ADR-055).

## Fait
- Règles acceptées, déplacées de `## Proposées` vers leur section : ADR-061
  (elle remplace la règle du parseur par mot-clé), ADR-062, ADR-064 et ADR-065.
  Leur code est livré (tickets 611 à 620, 650, 673). ADR-067 reste proposée
  jusqu'au ticket-705.
- E2 et E7 : la règle provider nomme le run `rapide` (ADR-059) et le défaut
  `agent_sdk`.
- E3 : la racine d'écriture est le projet ou son worktree (ADR-056).
- E4 : le mode d'artefacts suit la façon dont le projet est arrivé (ADR-023).
- E6 : ADR-013 nomme le store de run.
- C8 : `CLAUDE.md` donne le plafond testé (300) ;
  `test_claude_md_states_the_enforced_length` le relie à `PLAFOND_GENERAL`.
- C9 : composants et fichiers en PascalCase, hooks et `lib/` en camelCase.
- C6 : `write-adr`, `code-review` et `projects/ide-core/CLAUDE.md` disent
  que `contraintes.md` part par rôle et que `decisions.md` ne sert qu'en repli.

## Ce que ça ne fait pas
- E5 (règle `LLMProvider` gardée pour les routeurs seuls) : sans changement
- Ni renommage de fichiers, ni traduction des noms de tests (K3, K4)
