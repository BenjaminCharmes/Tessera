---
id: ticket-688
title: "Pipeline stages split by stage"
type: refactor
status: todo
priority: low
agent: codeur
depends_on: []
created: 2026-10-29
---

# ticket-688 — `pipeline_stages.py` découpé par étape

## Objectif
Un module par étape du pipeline, aucun au-dessus du plafond général.

## Contexte
`services/pipeline_stages.py` (840 lignes) porte quatre étapes en fonctions de
module : branche (`ensure_clean_tree`, `create_branch`, `_basculer` : 62-285),
production (`run_coder`, captures de diff : 286-549), tests (`run_tests` :
550-649), audit, revue et validation (650-840). `docs/audit/refactos.md` §1.

## Critères d'acceptation
- [ ] Aucun des modules issus du découpage ne dépasse 300 lignes ; l'entrée de `services/pipeline_stages.py` disparaît de `PLAFONDS` (le cliquet réclame son retrait si le fichier n'existe plus)
- [ ] `grep -rnE "pipeline_stages( import|\.)" backend/src backend/tests` ne rend aucune ligne (import ni cible de `patch`) : pas de module de ré-export
- [ ] Avant de déplacer, la PR relève les cibles de `patch("tessera.services.pipeline_stages.…")` des tests et les liste ; toutes sont réécrites vers le nouveau module
- [ ] `run_coder`, `run_tests`, `_basculer` et `run_security_audit` gardent leur signature ; les tests existants passent sans changement de leurs attendus
- [ ] `uv run pytest` et `uv run mypy` passent

## Ce que ça ne fait pas
- Ne change pas la logique d'une étape, ni l'ordre où `Orchestrator` les appelle
- Ne touche pas à `pipeline_outcomes.py`, cohérent à 490 lignes
