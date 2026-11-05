---
id: ticket-816
title: "The pipeline modules move to services/pipeline"
type: refactor
status: todo
pr_number: null
priority: low
agent: codeur
depends_on: [ticket-815]
estimated_days: 1
created: 2026-11-05
---

# ticket-816 — Les modules du pipeline passent dans `services/pipeline/`

## Objectif

Les trente et un modules du domaine `pipeline` (phases et orchestration d'un run) vivent dans
`services/pipeline/`, à comportement constant.

## Contexte

ADR-074 ; section `pipeline` de `memory/services-domaines.md`. Plus gros déplacement, et le plus
patché par chaîne : `orchestrator`, `run_registry` et `run_lock` sont aussi touchés par
`backend/tests/conftest.py`. ADR-008 et ADR-038 (orchestrateur sans état, `RunLock`) ne bougent pas.

## Ce que le ticket fait

- Lance `scripts/deplacer_domaine.py pipeline`, relit le diff, lance la suite.
- Relit `backend/tests/conftest.py` : `from tessera.services import ticket_service`,
  `run_registry`, `signalements_en_attente` y sont importés comme modules.

## Critères d'acceptation

- [ ] Les trente et un modules de la section `pipeline` sont sous `services/pipeline/`, aucun
      n'est resté à plat
- [ ] `A_DEPLACER` n'a plus d'entrée `pipeline`, `ECARTS_DOMAINES` n'a grandi d'aucune ligne
- [ ] Aucune occurrence des anciens chemins pointés ne reste dans `backend/src`, `backend/tests`,
      `scripts/`, `Makefile`
- [ ] Le diff n'est que des renommages et des lignes d'import ou de chaîne ; la suite passe

## Ce que ça ne fait pas

Aucun changement de comportement. Les modules de la file (`file`) sont déjà déplacés.

## Risques

Une chaîne de patch ratée sur `orchestrator` désarme un test de run sans l'échouer : relire les
restes de chemins avec `grep`, module par module.
