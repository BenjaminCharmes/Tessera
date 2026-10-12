---
id: ticket-403
title: "A dependent ticket starts from the base realigned onto its dependency's merge, on every project"
type: fix
status: done
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-12
---

# ticket-403 — Un ticket dépendant part de la base réalignée

## Objectif

Qu'un ticket qui dépend d'un autre parte d'une base qui contient le merge de
cette dépendance, quel que soit le mode de livraison du projet.

## Contexte

Le 2026-10-12, sur ide-core, le ticket-400 (`depends_on: ticket-399`) a été
bloqué après trois tours : son critère 5 portait sur la vue `ProjetsView`,
qui n'existait pas sur sa branche. Chronologie :
- la PR #373 du 399 a été mergée à 09:34:45 ;
- la branche du 400 a été créée à 09:34:48.

L'attente de la dépendance (`_attendre_si_dependant`) avait bien fonctionné,
mais la base **locale** n'avait pas été réalignée sur le squash distant. Ce
réalignement (`sync_base_depuis_distant`, ticket-382) ne s'appliquait qu'aux
projets en `merge_without_ci`.

## Solution

- `_attendre_si_dependant` rend `None` (aucun ticket restant n'en dépend),
  `True` (mergé) ou `False` (non mergé : la file s'arrête).
- Sur `True`, `run_queue` appelle `_realigner_base`, extrait de
  `_attendre_merge_et_syncer` et partagé avec le chemin du ticket-382.

## Critères d'acceptation

- [x] Un test de `backend/tests/test_orchestrator_livraison.py` vérifie que, dans une file de trois tickets dont le deuxième dépend du premier, la base est réalignée après le merge du premier et avant le départ du deuxième, et qu'aucune attente ni aucun réalignement n'a lieu avant le troisième, qui ne dépend de rien
- [x] Les tests existants des files (`test_orchestrator_livraison.py`, `test_file_non_mergee.py`, `test_orchestrator.py`, `test_file_de_tickets.py`) passent sans modification

## Ce que ça ne fait pas

- Ne réaligne pas avant un ticket sans dépendance, sur un projet qui attend
  sa CI : il peut démarrer pendant que la PR précédente attend sa CI, comme
  aujourd'hui.
