---
id: ticket-838
title: "Two consecutive blocks with the same cause are reported"
type: feat
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: [ticket-837]
estimated_days: 1
created: 2026-11-05
---

# ticket-838 — Deux blocages consécutifs de même cause sont signalés

## Objectif

La règle `blocages_identiques` (ADR-078) : quand un ticket repart alors que ses deux derniers
runs ont fini `blocked` pour la même cause, on le dit avant la troisième tentative.

## Contexte

Spec `docs/superpowers/specs/2026-11-05-detecteur-d-anomalies-design.md`. Le 03/11, deux
livraisons ont été coupées par le réseau : chaque run, pris seul, était un blocage ordinaire. La
cause est `pipeline_runs.arret`. Deux messages de même nature ne diffèrent que par un nombre, un
chemin ou un identifiant : c'est ce que la signature efface.

## Solution

- `regles_historiques.py` : `signature_d_arret(arret) -> str | None` — première ligne de `arret`,
  en minuscules, nombres, hexadécimaux, chemins et chaînes entre guillemets remplacés par un
  marqueur, coupée à 120 caractères ; `None` si `arret` est vide.
- `blocages_identiques(derniers: Sequence[RunFini])` : les deux plus récents sont `blocked`, leurs
  signatures sont non nulles et égales. Clé `blocages:<id du plus récent>`.
- `lecture_historique.py` gagne `derniers_runs_finis(db_path, project_id, ticket_id, n=2)` : les
  lignes `single` finies, plus récentes d'abord (`started_at DESC, rowid DESC`), enveloppes et
  ligne ouverte exclues.
- Le ticket se valide sur deux `arret` réels de livraison coupée par le réseau, relevés dans
  `pipeline_runs` ; s'ils divergent d'une façon que la signature ne comprend pas, elle s'élargit
  ici, pas dans une règle ailleurs.

## Critères d'acceptation

- [x] `test_signature_d_arret_ignores_numbers_hashes_paths_and_quoted_strings`
- [x] `test_signature_d_arret_keeps_different_words_apart`
- [x] `test_signature_d_arret_empty_or_blank_is_none`
- [x] `test_signature_d_arret_cuts_at_120_chars` : deux causes identiques sur 120 caractères et
      différentes au 121e ont la même signature ; différentes au 120e, des signatures différentes
- [x] `test_blocages_identiques_two_blocked_with_the_same_cause_reports`
- [x] `test_blocages_identiques_one_run_only_is_none`
- [x] `test_blocages_identiques_a_different_cause_is_none`
- [x] `test_blocages_identiques_an_approved_run_in_between_is_none`
- [x] `test_blocages_identiques_only_the_two_latest_runs_count` (trois runs, le plus ancien
      d'une autre cause : signalé)
- [x] `test_derniers_runs_finis_excludes_envelopes_and_the_open_row`

## Ce que ça ne fait pas

N'empêche pas la troisième tentative : le détecteur ne relance ni n'interdit rien. Ne lit que
`arret`, jamais les événements du run.
