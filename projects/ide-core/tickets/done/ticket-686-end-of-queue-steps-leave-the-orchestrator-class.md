---
agent: codeur
created: 2026-10-29
depends_on:
- ticket-685
id: ticket-686
priority: low
status: done
title: End-of-queue steps leave the Orchestrator class
type: refactor
---

# ticket-686 — La fin de file hors de la classe `Orchestrator`

## Objectif
Documentation par lot, attente de merge, réalignement et nettoyage vivent hors
de la classe, dans un module qui reçoit l'orchestrateur comme les `pipeline_*`.

## Contexte
`services/orchestrator.py:991-1222` (≈ 230 lignes) : `_documenter_le_run` (89),
`_attendre_merge_et_syncer`, `_realigner_base`, `_finaliser_livraison`,
`_signaler_fichiers_non_suivis`, `_nettoyer_apres_file`, `_sur_la_base`.
`docs/audit/refactos.md` §3.

## Critères d'acceptation
- [ ] Ces sept méthodes ne sont plus définies dans la classe : `grep -n "def _documenter_le_run\|def _finaliser_livraison\|def _nettoyer_apres_file" backend/src/tessera/services/orchestrator.py` ne rend rien
- [ ] L'entrée de `services/orchestrator.py` dans `PLAFONDS` est baissée à 800 ou moins
- [ ] Le module neuf n'importe `Orchestrator` que sous `TYPE_CHECKING`, comme les autres `pipeline_*`
- [ ] Les tests de documentation par lot (ADR-035), d'attente de merge et de nettoyage passent sans changement de leurs attendus
- [ ] `uv run pytest` et `uv run mypy` passent

## Ce que ça ne fait pas
- Ne change ni l'ordre ni les conditions de la livraison (ADR-029, ADR-030, ADR-051)
- Ne touche pas à `livraison.py` (ticket-700)