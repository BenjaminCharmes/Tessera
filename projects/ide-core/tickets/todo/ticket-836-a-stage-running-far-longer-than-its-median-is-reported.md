---
id: ticket-836
title: "A stage running far longer than its median is reported"
type: feat
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: [ticket-835]
estimated_days: 1
created: 2026-11-05
---

# ticket-836 — Une étape bien plus longue que sa médiane est signalée

## Objectif

La règle `etape_longue` (ADR-078) : une étape ouverte dure plus de `max(3 × médiane, 5 min)`.
C'est elle qui aurait vu le testeur figé du 03/11, de 19 h à 7 h 48.

## Contexte

Spec `docs/superpowers/specs/2026-11-05-detecteur-d-anomalies-design.md`, sections « Les règles »
et « Les étapes ». Une étape se lit dans `agent_events` : un événement de début, un de fin (tableau
de la spec). Une étape jamais close n'entre pas dans la médiane qui la juge.

## Solution

- `services/anomalies/etapes.py`, pure : `Etape` (`nom`, `debut`, `fin | None`, `agent | None`) et
  `etapes_depuis(evenements) -> list[Etape]`. Un début rouvert sans fin entre les deux rend la
  première étape **abandonnée** : ni ouverte ni échantillon.
- `services/anomalies/regles_historiques.py` : `mediane_si_assez(echantillon, minimum=10)` et
  `etape_longue(etape, maintenant, passees_s, plancher_s=300.0)`. Clé
  `etape_longue:<étape>:<ts du début>`. La médiane est un `statistics.median`.
- `lecture_evenements.py` gagne `evenements_de_etapes(db_path, run_id, ticket_id)` : les
  événements de début et de fin d'un ticket, **hors** tokens et appels d'outils.
- `services/anomalies/lecture_historique.py` : `durees_passees(db_path, project_id, etape, n=20)`,
  les durées en secondes des 20 dernières étapes **closes** du projet, plus récentes d'abord.
  Lit une borne de lignes (200 par type), jamais toute la table.
- Une migration de `services/database.py` ajoute un index sur `agent_events (type, id)`.

## Critères d'acceptation

- [ ] `test_etapes_depuis_pairs_start_and_end_events_per_stage` (codeur, tests, sécurité,
      validation, documentation, livraison)
- [ ] `test_etapes_depuis_leaves_an_unclosed_stage_open`
- [ ] `test_etapes_depuis_marks_a_restarted_stage_as_abandoned`
- [ ] `test_etapes_depuis_keeps_review_and_validation_apart_when_they_overlap`
- [ ] `test_mediane_si_assez_9_samples_is_none` et `test_mediane_si_assez_10_samples_returns_median`
- [ ] `test_etape_longue_just_under_three_medians_is_none` et
      `test_etape_longue_just_over_three_medians_reports` (médiane 600 s : 1799 s puis 1801 s)
- [ ] `test_etape_longue_floor_300s_under_is_none` et `test_etape_longue_floor_300s_over_reports`
      (médiane 20 s : 299 s puis 301 s)
- [ ] `test_etape_longue_without_enough_samples_is_none` et `test_etape_longue_ignores_a_closed_stage`
- [ ] `test_durees_passees_returns_the_20_most_recent_closed_stages_of_the_project` (21 étapes
      closes : la plus ancienne sort ; un autre projet, une étape ouverte et une étape abandonnée
      sont exclus)
- [ ] `test_agent_events_index_exists_and_init_db_stays_idempotent` : l'index existe sur une base
      neuve et sur une base ancienne migrée

## Risques

Ce ticket modifie `backend/src/tessera/services/database.py`, qui n'est pas un fichier de
configuration de tests ; aucune porte de configuration n'est concernée.

## Ce que ça ne fait pas

Pas de coût, pas de blocage, pas de boucle. Pas de nouvel événement : les étapes se relisent dans
l'existant.
