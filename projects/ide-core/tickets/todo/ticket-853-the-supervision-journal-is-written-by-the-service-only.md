---
id: ticket-853
title: "The supervision journal is written by the service only"
type: feat
status: todo
priority: high
agent: codeur
depends_on: [ticket-851]
estimated_days: 1
created: 2026-11-05
pr_number: null
---

# ticket-853 — Le journal `memory/supervision.md`, écrit par le service seul

## Objectif

Chaque action du superviseur laisse une ligne datée ; un run ne peut pas y écrire.

## Contexte

ADR-080, spec §2 « Où il rend compte ». Même mécanique que `memory/lecons.md` (ADR-074,
tickets 801 et 804).

## Ce qu'il faut faire

- `services/supervision/superviseur_journal.py` : `ajouter_ligne(memory_dir, *, jour, action,
  cible, sha, resume)` et `lire_journal(memory_dir, depuis=None) -> list[LigneJournal]`. Format :
  une ligne `- AAAA-MM-JJ | action | cible | sha | résumé`, résumé ≤ 200 caractères sur une ligne.
  `action` : les quatre actions, plus `a_toi` (cas laissé à l'humain, `sha` vide) et `resolu`
  (clôt le cas `a_toi` de même cible). `cas_a_toi_ouverts(lignes)` rend les `a_toi` sans
  `resolu` ensuite. Fichier absent ou illisible : liste vide, jamais d'erreur.
- Un diff de run (codeur ou architect) qui touche `memory/supervision.md` met le run en
  `blocked`, comme `lecons.md` (`lecons_touchees.py` en est le modèle) ; une intervention du
  superviseur est la seule exception, reconnue par son type de run, jamais par le chemin.

## Critères d'acceptation

- [ ] `test_superviseur_journal.py::test_add_then_read_round_trips`
- [ ] `test_superviseur_journal.py::test_since_filters_older_lines`
- [ ] `test_superviseur_journal.py::test_unreadable_file_reads_as_empty`
- [ ] `test_superviseur_journal.py::test_multiline_summary_is_refused`
- [ ] `test_superviseur_journal.py::test_a_toi_case_is_open_until_a_resolu_line_follows`
- [ ] `test_superviseur_journal_touche.py::test_run_diff_touching_journal_blocks_the_run`
- [ ] `test_superviseur_journal_touche.py::test_supervision_run_is_not_blocked`

## Ce que ça ne fait pas

Ne décide rien ; n'affiche rien (tickets 860 et 861).
