---
id: ticket-714
title: "A local provider hands an oversized prompt straight to its fallback"
type: feat
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-30
---

# ticket-714 — Un provider local confie d'emblée un prompt trop gros à son repli

## Objectif
Un rôle sur Ollama peut déclarer une taille de prompt au-delà de laquelle il
part directement sur son repli, sans attendre 300 s un délai dépassé.

## Contexte
Dans la nuit du 29/10, le validateur d'ide-core (Ollama) a dépassé
`DELAI_LECTURE_S` (300 s, `backend/src/tessera/services/providers/ollama.py`)
sur les tickets 652, 653, 654 et 672. Après chacun, il est passé au repli Haiku
(`projects/ide-core/memory/pipeline-log.md`). Ces tickets portaient de gros
diffs (audits, conception). Chaque dépassement coûte 5 minutes perdues, puis
un appel Haiku qui aurait suffi d'emblée. Le repli existe pour deux causes :
une indisponibilité (ADR-046) et un run `rapide` (ADR-059).

## Solution proposée
Une clé optionnelle par rôle dans `agents.json`, `fallback_above_chars` (un
entier). Quand le provider principal du rôle est `ollama` et que le prompt
(système et utilisateur) dépasse cette taille, l'appel part sur le repli. Il
émet `provider_fallback` avec une raison qui donne la taille et le seuil, et
le journal le dit. Sans la clé, rien ne change. Sans repli déclaré, la clé est
ignorée.

## Critères d'acceptation
- [ ] `test_oversized_prompt_goes_to_the_fallback` (dans `backend/tests/test_provider_par_role.py`) : un rôle `ollama` avec `fallback_above_chars: 100` et un prompt de 500 caractères appelle le repli, jamais Ollama
- [ ] `test_prompt_under_the_threshold_stays_local` : un prompt de 50 caractères appelle Ollama
- [ ] `test_oversized_fallback_emits_its_reason` : l'événement `provider_fallback` porte la taille du prompt et le seuil
- [ ] `test_threshold_without_fallback_is_ignored` : sans `fallback` déclaré, Ollama est appelé quelle que soit la taille
- [ ] `test_threshold_is_ignored_for_a_cloud_provider` : un rôle `agent_sdk` avec la clé ne change pas de provider

## Ce que ça ne fait pas
- Ne change pas `DELAI_LECTURE_S`
- Ne règle pas le seuil d'ide-core : `agents.json` se modifie à la main après
  le merge (ADR-027). La valeur se choisit d'après les tailles de prompt des
  quatre dépassements.
