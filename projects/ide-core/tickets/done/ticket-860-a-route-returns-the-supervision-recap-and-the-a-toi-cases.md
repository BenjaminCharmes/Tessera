---
agent: codeur
created: 2026-11-05
depends_on:
- ticket-853
estimated_days: 1
id: ticket-860
pr_number: 952
priority: medium
status: done
title: A route returns the supervision recap and the A-toi cases
type: feat
---

# ticket-860 — Une route rend le récap du superviseur et ses cas « À toi »

## Objectif

`GET /api/v1/supervision/recap?depuis=AAAA-MM-JJ` rend ce que le superviseur a fait depuis une
date, et ce qu'il a laissé à Benjamin.

## Contexte

ADR-080, spec §2 « Où il rend compte ». La réponse « À toi » de ticket-831 porte déjà
`lecons_proposees` ; la route de ce ticket est en lecture seule et ne confère aucun pouvoir.

## Ce qu'il faut faire

- Router `routers/supervision_recap.py` : `lignes` (de `lire_journal`, plus récentes d'abord,
  200 au plus), `a_toi` (`cas_a_toi_ouverts` du journal, ticket-853 : règle sensible, tri impossible, deux
  échecs) avec la recommandation du superviseur, `depuis` répété. Lecture seule ; un `Origin` déclaré
  n'est pas requis pour lire, aucune écriture n'existe.
- La réponse de la route « À toi » du ticket-831 gagne `superviseur_a_toi: int` ; 0 sans
  fichier, jamais une erreur.
- `depuis` illisible : 422 ; futur : liste vide.

## Critères d'acceptation

- [ ] `test_supervision_recap.py::test_recap_returns_lines_since_the_date_newest_first`
- [ ] `test_supervision_recap.py::test_recap_without_journal_is_empty_not_an_error`
- [ ] `test_supervision_recap.py::test_bad_date_is_422`
- [ ] `test_supervision_recap.py::test_a_toi_count_matches_open_cases`
- [ ] `test_supervision_recap.py::test_recap_has_no_write_method`

## Ce que ça ne fait pas

Aucun bouton ni écriture (ticket-861 affiche seulement). Pas d'annulation : défaire est un
`git revert` du commit nommé dans la ligne.