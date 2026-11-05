---
id: ticket-822
title: "The pipeline modules move to services/pipeline"
type: refactor
status: done
pr_number: null
priority: low
agent: codeur
depends_on: [ticket-821]
estimated_days: 1
created: 2026-11-05
---

# ticket-822 — Les modules du pipeline passent dans `services/pipeline/`

## Objectif

Les trente et un modules du domaine `pipeline` (phases et orchestration d'un run) vivent dans
`services/pipeline/`, à comportement constant.

## Contexte

ADR-076 ; section `pipeline` de `memory/services-domaines.md`. Plus gros déplacement, et le plus
patché par chaîne : `orchestrator`, `run_registry` et `run_lock` sont aussi touchés par
`backend/tests/conftest.py`. ADR-008 et ADR-038 (orchestrateur sans état, `RunLock`) ne bougent pas.

## Ce que le ticket fait

- Lance `scripts/deplacer_domaine.py pipeline`, relit le diff, lance la suite.
- Relit `backend/tests/conftest.py` : `from tessera.services import ticket_service`,
  `run_registry`, `signalements_en_attente` y sont importés comme modules.

## Critères d'acceptation

- [x] Les trente et un modules de la section `pipeline` sont sous `services/pipeline/`, aucun
      n'est resté à plat
- [x] `A_DEPLACER` n'a plus d'entrée `pipeline`, `ECARTS_DOMAINES` n'a grandi d'aucune ligne
- [x] Aucune occurrence des anciens chemins pointés ne reste dans `backend/src`, `backend/tests`,
      `scripts/`, `Makefile`
- [x] Le diff n'est que des renommages et des lignes d'import ou de chaîne ; la suite passe

## Ce que ça ne fait pas

Aucun changement de comportement. Les modules de la file (`file`) sont déjà déplacés.

## Risques

Une chaîne de patch ratée sur `orchestrator` désarme un test de run sans l'échouer : relire les
restes de chemins avec `grep`, module par module.

## Notes de réalisation

Le domaine compte trente-neuf modules, pas trente et un : `scripts/domaines_services.py` fait foi. Retouches à la main : `test_lecons_gardees.py` lit `orchestrator.py` et `pipeline_outcomes.py` sous `services/pipeline/` ; la liste triée de `test_run_worktree.py` est retriée ; `orchestrator.py` passait à 638 lignes (imports découpés par le script) : trois imports regroupés sur une ligne chacun le ramènent à 627, et son plafond descend à 627 (cliquet). `test_pipeline_fin_de_file.py` lit le dossier du module et `test_modeles_par_defaut.py` parcourt `services/` récursivement : aucun des deux ne change. `conftest.py` importe `run_registry` et `signalements_en_attente` depuis `services.pipeline`.
